import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.forms import get_custom_form_data, submit_custom_form
from buzz.api.forms.exceptions import FormNotAvailable, LoginRequired
from buzz.api.sponsorships import (
	get_enquiry_form,
	get_sponsorship_details,
	get_user_sponsorship_inquiries,
	submit_enquiry_form,
)
from buzz.api.sponsorships.exceptions import EnquiryNotAccessible
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team


class SponsorFormTestCase(IntegrationTestCase):
	@staticmethod
	def ensure_category():
		name = "Sponsor Form Test Category"
		if not frappe.db.exists("Event Category", name):
			frappe.get_doc({"doctype": "Event Category", "name": name}).insert(ignore_permissions=True)
		return name

	@staticmethod
	def ensure_host():
		name = "Sponsor Form Test Host"
		host = frappe.db.get_value("Event Host", {"host_name": name})
		if not host:
			host = (
				frappe.get_doc({"doctype": "Event Host", "host_name": name})
				.insert(ignore_permissions=True)
				.name
			)
		return host

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()
		self.category = self.ensure_category()
		self.host = self.ensure_host()
		self.team = create_owned_team(f"Sponsor Forms {frappe.generate_hash(length=6)}", "Administrator")
		self.event = self.make_event()
		self.form = frappe.get_doc("Sponsor Enquiry Form", {"event": self.event.name})
		self.form.publish = 1
		self.form.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def make_event(self):
		return frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": f"Sponsor Form {frappe.generate_hash(length=6)}",
				"start_date": "2030-01-01",
				"end_date": "2030-01-01",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"category": self.category,
				"host": self.host,
				"team": self.team,
				"is_published": 1,
			}
		).insert(ignore_permissions=True)

	def form_values(self, **extra):
		return {"company_name": "Acme", "company_logo": "/files/acme.png", **extra}

	def add_question(self, **question):
		self.form.append(
			"custom_fields",
			{
				"label": "Budget",
				"fieldname": "budget",
				"fieldtype": "Number",
				"enabled": 1,
				**question,
			},
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

	def test_guest_is_refused_unless_the_form_allows_guest_submissions(self):
		frappe.set_user("Guest")
		with self.assertRaises(LoginRequired):
			submit_enquiry_form(self.event.route, self.form_values())

		frappe.set_user("Administrator")
		self.form.allow_guest_submissions = 1
		self.form.save(ignore_permissions=True)
		frappe.set_user("Guest")

		self.assertFalse(get_enquiry_form(self.event.route).closed)

	def test_archiving_unpublishes_the_form_without_reopening_it_on_republish(self):
		self.event.archive_event()
		self.form.reload()
		self.assertFalse(self.form.publish)

		self.event.is_published = 1
		self.event.save(ignore_permissions=True)
		self.form.reload()
		self.assertFalse(self.form.publish)


class TestSponsorFormSubmission(SponsorFormTestCase):
	def make_user(self, email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Sponsor",
				"roles": [{"role": "Buzz User"}],
			}
		)
		return user.insert(ignore_permissions=True).name

	def test_submission_records_form_and_drops_forged_values(self):
		name = submit_enquiry_form(
			self.event.route,
			self.form_values(
				event="forged", status="Paid", enquiry_form="forged", contact_email="stranger@example.com"
			),
		)
		enquiry = frappe.get_doc("Sponsorship Enquiry", name)

		self.assertEqual(str(enquiry.event), str(self.event.name))
		self.assertEqual(enquiry.enquiry_form, self.form.name)
		self.assertEqual(enquiry.status, "Approval Pending")
		self.assertFalse(enquiry.contact_email)

	def test_generic_submission_delegates_to_dedicated_service(self):
		submit_custom_form(self.event.route, self.form.route, self.form_values(company_name="Generic"))
		enquiry = frappe.get_last_doc("Sponsorship Enquiry", filters={"company_name": "Generic"})

		self.assertEqual(enquiry.enquiry_form, self.form.name)

	def test_standard_field_validation_is_preserved(self):
		with self.assertRaises(frappe.MandatoryError):
			submit_enquiry_form(self.event.route, {"company_logo": "/files/acme.png"})

		with self.assertRaises(frappe.ValidationError):
			submit_enquiry_form(self.event.route, self.form_values(website="not-a-url"))

		with self.assertRaises(frappe.ValidationError):
			submit_enquiry_form(self.event.route, self.form_values(phone="not-a-phone"))

	def test_cross_event_tier_is_rejected(self):
		other_event = self.make_event()
		tier = frappe.get_doc(
			{
				"doctype": "Sponsorship Tier",
				"event": other_event.name,
				"title": "Other tier",
				"price": 100,
				"currency": "INR",
			}
		).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			submit_enquiry_form(self.event.route, self.form_values(tier=tier.name))

	def test_disabled_tier_is_excluded_from_link_options(self):
		enabled = self.make_tier("Available")
		disabled = self.make_tier("Retired", enabled=0)

		tier_field = next(
			field for field in get_enquiry_form(self.event.route).form_fields if field["fieldname"] == "tier"
		)
		values = {option["value"] for option in tier_field["link_options"]}

		self.assertIn(enabled.name, values)
		self.assertNotIn(disabled.name, values)

	def test_disabled_tier_submission_is_rejected(self):
		tier = self.make_tier("Retired", enabled=0)

		with self.assertRaises(frappe.ValidationError):
			submit_enquiry_form(self.event.route, self.form_values(tier=tier.name))

	def make_tier(self, title, enabled=1):
		return frappe.get_doc(
			{
				"doctype": "Sponsorship Tier",
				"event": self.event.name,
				"title": title,
				"price": 100,
				"currency": "INR",
				"enabled": enabled,
			}
		).insert(ignore_permissions=True)

	def test_guest_submission_requires_a_valid_contact_email(self):
		self.form.allow_guest_submissions = 1
		self.form.save(ignore_permissions=True)
		frappe.set_user("Guest")

		with self.assertRaises(frappe.MandatoryError):
			submit_enquiry_form(self.event.route, self.form_values())

		with self.assertRaises(frappe.ValidationError):
			submit_enquiry_form(self.event.route, self.form_values(contact_email="invalid"))

		name = submit_enquiry_form(self.event.route, self.form_values(contact_email="applicant@example.com"))
		enquiry = frappe.get_doc("Sponsorship Enquiry", name)
		self.assertEqual(enquiry.owner, "Guest")
		self.assertEqual(enquiry.contact_email, "applicant@example.com")

	def test_contact_email_addresses_mail_but_grants_no_access(self):
		self.form.allow_guest_submissions = 1
		self.form.save(ignore_permissions=True)
		frappe.set_user("Guest")
		name = submit_enquiry_form(self.event.route, self.form_values(contact_email="applicant@example.com"))
		enquiry = frappe.get_doc("Sponsorship Enquiry", name)

		self.assertEqual(enquiry.contact_recipient, "applicant@example.com")

		# The address is never verified, so holding that mailbox proves nothing.
		applicant = self.make_user("applicant@example.com")
		frappe.set_user(applicant)
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
			submit_enquiry_form(
				self.event.route, self.form_values(), custom_fields_data={"newsletter": False}
			)

		name = submit_enquiry_form(
			self.event.route,
			self.form_values(),
			custom_fields_data={"budget": 0, "newsletter": False, "package": "Gold"},
		)
		answers = {
			row.fieldname: row.value for row in frappe.get_doc("Sponsorship Enquiry", name).additional_fields
		}
		self.assertEqual(answers, {"budget": "0", "newsletter": "0", "package": "Gold"})

		with self.assertRaises(frappe.ValidationError):
			submit_enquiry_form(
				self.event.route,
				self.form_values(),
				custom_fields_data={"budget": 10, "newsletter": 1, "package": "Bronze"},
			)

		with self.assertRaises(frappe.ValidationError):
			submit_enquiry_form(
				self.event.route,
				self.form_values(),
				custom_fields_data={"budget": 10, "newsletter": 1, "unknown": "x"},
			)
