import json

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.forms import get_custom_form_data, submit_custom_form
from buzz.api.forms.exceptions import FormNotAvailable
from buzz.api.sponsorships import (
	get_enquiry_form,
	get_sponsorship_details,
	get_user_sponsorship_inquiries,
	submit_enquiry_form,
)
from buzz.api.sponsorships.exceptions import EnquiryNotAccessible
from buzz.tests.factories import BuzzEventFactory, BuzzFormFactory, SponsorshipTierFactory, UserFactory

APPLICANT = "sponsor-applicant@example.com"


class SponsorFormTestCase(IntegrationTestCase):
	def setUp(self):
		self.enterContext(self.set_user("Administrator"))
		self.event = BuzzEventFactory.create()
		self.form = frappe.get_doc(
			"Buzz Form", {"event": self.event.name, "form_doctype": "Sponsorship Enquiry"}
		)
		self.form.publish = 1
		self.form.save(ignore_permissions=True)

	def submit(self, *args, **kwargs):
		"""Enquiries come from website users; a System User would pass checks they must meet."""
		with self.set_user(UserFactory.create_once(APPLICANT).name):
			return submit_enquiry_form(*args, **kwargs)

	def submit_generic(self, *args, **kwargs):
		with self.set_user(UserFactory.create_once(APPLICANT).name):
			return submit_custom_form(*args, **kwargs)

	def form_values(self, **extra):
		return {"company_name": "Acme", "company_logo": "/files/acme.png", **extra}

	def add_question(self, **question):
		BuzzFormFactory.append_question(
			self.form,
			**{"label": "Budget", "fieldname": "budget", "fieldtype": "Number", "enabled": 1, **question},
		)
		self.form.save(ignore_permissions=True)


class TestSponsorFormData(SponsorFormTestCase):
	def test_dedicated_and_generic_endpoints_return_the_same_form(self):
		dedicated = get_enquiry_form(self.event.route)
		generic = get_custom_form_data(self.event.route, self.form.route)

		self.assertEqual(dedicated.form_title, "Sponsorship Enquiry")
		self.assertEqual(dedicated.submission_method, "buzz.api.sponsorships.submit_enquiry_form")
		self.assertEqual(generic.submission_method, dedicated.submission_method)

	def test_unpublished_form_is_not_available(self):
		self.form.publish = 0
		self.form.save(ignore_permissions=True)

		with self.assertRaises(FormNotAvailable):
			get_enquiry_form(self.event.route)

	def test_guest_can_open_the_form_with_a_required_contact_email(self):
		with self.set_user("Guest"):
			contact = self.contact_field()
			closed = get_enquiry_form(self.event.route).closed

		self.assertFalse(closed)
		self.assertTrue(contact["reqd"])
		self.assertFalse(contact["default"])

	def test_signed_in_user_gets_their_email_prefilled(self):
		with self.set_user(UserFactory.create_once(APPLICANT).name):
			contact = self.contact_field()

		self.assertTrue(contact["reqd"])
		self.assertEqual(contact["default"], APPLICANT)

	def test_hiding_contact_email_is_refused(self):
		for row in self.form.questions:
			if row.fieldname == "contact_email":
				row.enabled = 0
		with self.assertRaises(frappe.ValidationError):
			self.form.save(ignore_permissions=True)

	def test_archiving_unpublishes_the_form_without_reopening_it_on_republish(self):
		self.event.archive_event()
		self.form.reload()
		self.assertFalse(self.form.publish)

		self.event.is_published = 1
		self.event.save(ignore_permissions=True)
		self.form.reload()
		self.assertFalse(self.form.publish)

	def contact_field(self):
		fields = get_enquiry_form(self.event.route).form_fields
		return next(field for field in fields if field["fieldname"] == "contact_email")


class TestSponsorFormSubmission(SponsorFormTestCase):
	def test_submission_records_form_and_drops_forged_values(self):
		name = self.submit(
			self.event.route,
			self.form_values(event="forged", status="Paid", enquiry_form="forged"),
		)
		enquiry = frappe.get_doc("Sponsorship Enquiry", name)

		self.assertEqual(str(enquiry.event), str(self.event.name))
		self.assertEqual(enquiry.enquiry_form, self.form.name)
		self.assertEqual(enquiry.status, "Approval Pending")

	def test_signed_in_submission_without_contact_email_uses_their_email(self):
		name = self.submit(self.event.route, self.form_values())

		self.assertEqual(frappe.db.get_value("Sponsorship Enquiry", name, "contact_email"), APPLICANT)

	def test_signed_in_user_may_give_another_contact_email(self):
		name = self.submit(self.event.route, self.form_values(contact_email="team@example.com"))

		enquiry = frappe.get_doc("Sponsorship Enquiry", name)
		self.assertEqual(enquiry.contact_email, "team@example.com")
		self.assertEqual(enquiry.owner, APPLICANT)

	def test_generic_submission_delegates_to_dedicated_service(self):
		self.submit_generic(self.event.route, self.form.route, self.form_values(company_name="Generic"))
		enquiry = frappe.get_last_doc("Sponsorship Enquiry", filters={"company_name": "Generic"})

		self.assertEqual(enquiry.enquiry_form, self.form.name)

	def test_standard_field_validation_is_preserved(self):
		with self.assertRaises(frappe.MandatoryError):
			self.submit(self.event.route, {"company_logo": "/files/acme.png"})

		with self.assertRaises(frappe.ValidationError):
			self.submit(self.event.route, self.form_values(website="not-a-url"))

		with self.assertRaises(frappe.ValidationError):
			self.submit(self.event.route, self.form_values(phone="not-a-phone"))

	def test_cross_event_tier_is_rejected(self):
		tier = SponsorshipTierFactory.create()

		with self.assertRaises(frappe.ValidationError):
			self.submit(self.event.route, self.form_values(tier=tier.name))

	def test_disabled_tier_is_excluded_from_link_options(self):
		enabled = SponsorshipTierFactory.create(event=self.event.name)
		disabled = SponsorshipTierFactory.create(event=self.event.name, enabled=0)

		tier_field = next(
			field for field in get_enquiry_form(self.event.route).form_fields if field["fieldname"] == "tier"
		)
		values = {option["value"] for option in tier_field["link_options"]}

		self.assertIn(enabled.name, values)
		self.assertNotIn(disabled.name, values)

	def test_disabled_tier_submission_is_rejected(self):
		tier = SponsorshipTierFactory.create(event=self.event.name, enabled=0)

		with self.assertRaises(frappe.ValidationError):
			self.submit(self.event.route, self.form_values(tier=tier.name))

	def test_guest_submission_requires_a_valid_contact_email(self):
		self.enterContext(self.set_user("Guest"))

		with self.assertRaises(frappe.MandatoryError):
			submit_enquiry_form(self.event.route, self.form_values())

		with self.assertRaises(frappe.ValidationError):
			submit_enquiry_form(self.event.route, self.form_values(contact_email="invalid"))

		name = submit_enquiry_form(self.event.route, self.form_values(contact_email="applicant@example.com"))
		enquiry = frappe.get_doc("Sponsorship Enquiry", name)
		self.assertEqual(enquiry.owner, "Guest")
		self.assertEqual(enquiry.contact_email, "applicant@example.com")

	def test_contact_email_addresses_mail_but_grants_no_access(self):
		with self.set_user("Guest"):
			name = submit_enquiry_form(
				self.event.route, self.form_values(contact_email="applicant@example.com")
			)
		enquiry = frappe.get_doc("Sponsorship Enquiry", name)

		self.assertEqual(enquiry.contact_recipient, "applicant@example.com")

		# The address is never verified, so holding that mailbox proves nothing.
		with self.set_user(UserFactory.create_once("applicant@example.com").name):
			with self.assertRaises(EnquiryNotAccessible):
				get_sponsorship_details(name)
			self.assertNotIn(name, {row.name for row in get_user_sponsorship_inquiries()})

	def test_custom_answers_validate_required_zero_and_options(self):
		self.add_question(mandatory=1)
		self.add_question(
			label="Newsletter",
			fieldname="newsletter",
			fieldtype="Check",
			mandatory=1,
		)
		self.add_question(label="Package", fieldname="package", fieldtype="Select", options="Gold\nSilver")

		with self.assertRaises(frappe.MandatoryError):
			self.submit(self.event.route, self.form_values(), custom_fields_data={"newsletter": False})

		name = self.submit(
			self.event.route,
			self.form_values(),
			custom_fields_data={"budget": 0, "newsletter": False, "package": "Gold"},
		)
		answers = {
			row.fieldname: row.value for row in frappe.get_doc("Sponsorship Enquiry", name).additional_fields
		}
		self.assertEqual(answers, {"budget": "0", "newsletter": "0", "package": "Gold"})

		with self.assertRaises(frappe.ValidationError):
			self.submit(
				self.event.route,
				self.form_values(),
				custom_fields_data={"budget": 10, "newsletter": 1, "package": "Bronze"},
			)

		with self.assertRaises(frappe.ValidationError):
			self.submit(
				self.event.route,
				self.form_values(),
				custom_fields_data={"budget": 10, "newsletter": 1, "unknown": "x"},
			)


class TestSponsorFormConditions(SponsorFormTestCase):
	def setUp(self):
		super().setUp()
		self.gold = SponsorshipTierFactory.create(event=self.event.name, title="Gold")
		self.silver = SponsorshipTierFactory.create(event=self.event.name, title="Silver")

	def test_an_answer_to_a_hidden_question_is_dropped(self):
		self.add_question(depends_on=condition("tier", "=", self.gold.name))

		name = self.submit(
			self.event.route, self.form_values(tier=self.silver.name), custom_fields_data={"budget": 1000}
		)

		self.assertEqual(self.answers_of(name), {})

	def test_a_shown_question_keeps_its_answer(self):
		self.add_question(depends_on=condition("tier", "=", self.gold.name))

		name = self.submit(
			self.event.route, self.form_values(tier=self.gold.name), custom_fields_data={"budget": 1000}
		)

		self.assertEqual(self.answers_of(name), {"budget": "1000"})

	def test_a_hidden_mandatory_question_does_not_block_submit(self):
		self.add_question(mandatory=1, depends_on=condition("tier", "=", self.gold.name))

		self.assertTrue(self.submit(self.event.route, self.form_values(tier=self.silver.name)))
		with self.assertRaises(frappe.MandatoryError):
			self.submit(self.event.route, self.form_values(tier=self.gold.name))

	def test_a_conditionally_required_question_must_be_answered_when_shown(self):
		self.add_question(mandatory_depends_on=condition("tier", "=", self.gold.name))

		with self.assertRaises(frappe.MandatoryError):
			self.submit(self.event.route, self.form_values(tier=self.gold.name))
		self.assertTrue(self.submit(self.event.route, self.form_values(tier=self.silver.name)))

	def test_form_data_carries_help_text_and_rules(self):
		self.add_question(description="In dollars", depends_on=condition("tier", "=", self.gold.name))

		self.assertEqual(self.definition_of("budget").description, "In dollars")
		rules = get_enquiry_form(self.event.route).logic_rules
		self.assertEqual(rules[0]["conditions"], [["tier", "=", self.gold.name]])
		self.assertEqual(rules[0]["actions"], [["show", "budget"]])

	def definition_of(self, fieldname: str):
		definitions = get_enquiry_form(self.event.route).custom_fields
		return next(definition for definition in definitions if definition.fieldname == fieldname)

	def answers_of(self, enquiry: str) -> dict:
		rows = frappe.get_doc("Sponsorship Enquiry", enquiry).additional_fields
		return {row.fieldname: row.value for row in rows}


def condition(fieldname: str, operator: str, value) -> str:
	return json.dumps([[fieldname, operator, value]])
