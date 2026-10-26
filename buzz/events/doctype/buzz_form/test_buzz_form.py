import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime

from buzz.events.doctype.buzz_form.form_types import FormType, form_type
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzFormFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventTicketTypeFactory,
	SponsorshipTierFactory,
	UserFactory,
)


class TestBuzzFormClosing(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		owner = UserFactory.create_once("form-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(owner).name
		cls.manager = cls.add_member("form-manager@example.com", cls.team, "Manager")
		cls.viewer = cls.add_member("form-viewer@example.com", cls.team, "Viewer")
		cls.frontdesk = cls.add_member("form-frontdesk@example.com", cls.team, "Frontdesk")
		other_team = BuzzTeamFactory.create_owned_by().name
		cls.other_team_manager = cls.add_member("form-other-manager@example.com", other_team, "Manager")

	def setUp(self):
		self.event = str(BuzzEventFactory.create(team=self.team).name)
		self.form = self.form_of(self.event)

	def test_closing_and_opening_round_trips(self):
		self.assertFalse(self.form.set_closed(False))
		self.assertTrue(self.form_of(self.event).publish)

		self.assertTrue(self.form.set_closed(True))
		self.assertFalse(self.form_of(self.event).publish)

	def test_opening_clears_a_past_cutoff(self):
		self.form.auto_close_at = add_days(now_datetime(), -1)
		self.form.save()

		self.assertFalse(self.form.set_closed(False))
		self.assertIsNone(self.form_of(self.event).auto_close_at)

	def test_opening_needs_a_published_event(self):
		frappe.db.set_value("Buzz Event", self.event, "is_published", 0)

		with self.assertRaises(frappe.ValidationError):
			self.form.set_closed(False)

	def test_archived_event_stays_closed(self):
		self.form.set_closed(False)
		frappe.get_doc("Buzz Event", self.event).archive_event()
		form = self.form_of(self.event)

		self.assertTrue(form.is_closed)
		with self.assertRaises(frappe.ValidationError):
			form.set_closed(False)

	def test_team_manager_may_toggle(self):
		with self.set_user(self.manager):
			self.assertTrue(self.form_of(self.event).set_closed(True))

	def test_outsiders_cannot_write(self):
		outsiders = {
			"viewer": self.viewer,
			"frontdesk": self.frontdesk,
			"other team manager": self.other_team_manager,
			"guest": "Guest",
		}
		for label, user in outsiders.items():
			with self.subTest(label), self.set_user(user):
				form = frappe.get_doc("Buzz Form", self.form.name, check_permission=False)
				with self.assertRaises(frappe.PermissionError):
					form.check_permission("write")
				with self.assertRaises(frappe.PermissionError):
					form.set_closed(True)

	@classmethod
	def add_member(cls, email: str, team: str, team_role: str) -> str:
		user = UserFactory.create_once(email).name
		BuzzTeamMembershipFactory.create(team=team, user=user, team_role=team_role)
		return user

	def form_of(self, event: str):
		return frappe.get_doc("Buzz Form", {"event": event, "form_doctype": "Sponsorship Enquiry"})


class TestBuzzFormValidation(IntegrationTestCase):
	def setUp(self):
		self.event = BuzzEventFactory.create()
		self.form = frappe.get_doc(
			"Buzz Form", {"event": self.event.name, "form_doctype": "Sponsorship Enquiry"}
		)

	def test_the_event_cannot_change_after_insert(self):
		self.form.event = BuzzEventFactory.create().name

		with self.assertRaises(frappe.CannotChangeConstantError):
			self.form.save()

	def test_the_form_doctype_cannot_change_after_insert(self):
		self.form.form_doctype = "Talk Proposal"

		with self.assertRaises(frappe.CannotChangeConstantError):
			self.form.save()

	def test_another_form_of_the_event_cannot_use_the_same_route(self):
		BuzzFormFactory.create(event=self.event.name, route="shared-route")

		with self.assertRaises(frappe.ValidationError):
			BuzzFormFactory.create(event=self.event.name, route="shared-route")

	def test_a_default_form_route_is_refused(self):
		# Every event opens with its own feedback and talk proposal forms.
		with self.assertRaises(frappe.ValidationError):
			BuzzFormFactory.create(event=self.event.name, route="propose-talk")

	def test_the_same_route_on_another_event_is_allowed(self):
		event = BuzzEventFactory.create()
		BuzzFormFactory.create(event=self.event.name, route="shared-route")

		self.assertTrue(BuzzFormFactory.create(event=event.name, route="shared-route").name)

	def test_a_second_sponsorship_form_for_one_event_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			BuzzFormFactory.create(
				event=self.event.name, form_doctype="Sponsorship Enquiry", route="another-sponsorship"
			)

	def test_a_second_talk_proposal_form_for_one_event_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			BuzzFormFactory.create(
				event=self.event.name, form_doctype="Talk Proposal", route="another-proposal"
			)

	def test_two_feedback_forms_with_different_routes_are_allowed(self):
		for route in ("first-feedback", "second-feedback"):
			with self.subTest(route):
				self.assertTrue(BuzzFormFactory.create(event=self.event.name, route=route).name)

	def test_contact_email_cannot_be_excluded(self):
		self.form.excluded_fields = "contact_email"

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_a_reserved_fieldname_is_refused(self):
		self.add_question(fieldname="tier")

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_a_duplicate_fieldname_is_refused(self):
		self.add_question(fieldname="budget")
		self.add_question(fieldname="budget")

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_a_fieldname_must_start_with_a_letter(self):
		self.add_question(fieldname="1st_choice")

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_a_saved_fieldname_cannot_be_renamed(self):
		self.add_question(fieldname="budget")
		self.form.save()
		self.form.questions[0].fieldname = "spend"

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_questions_need_an_additional_fields_table(self):
		form = BuzzFormFactory.create(event=self.event.name, form_doctype="Buzz Tag", route="tag-form")
		form.append("questions", {"label": "Why", "fieldname": "why", "fieldtype": "Data"})

		with self.assertRaises(frappe.ValidationError):
			form.save()

	def test_a_condition_that_is_not_json_is_refused(self):
		self.add_question(fieldname="budget", depends_on="[not json")

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_an_unknown_condition_operator_is_refused(self):
		self.add_question(fieldname="budget", depends_on=condition("tier", "like", "Gold"))

		with self.assertRaisesRegex(frappe.ValidationError, "Condition on Budget"):
			self.form.save()

	def test_a_condition_naming_its_own_question_is_refused(self):
		self.add_question(fieldname="budget", depends_on=condition("budget", ">", 5000))

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_a_condition_naming_a_question_below_is_refused(self):
		self.add_question(fieldname="budget", depends_on=condition("spend", ">", 5000))
		self.add_question(fieldname="spend")

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_a_condition_naming_a_tier_of_another_event_is_refused(self):
		tier = SponsorshipTierFactory.create()
		self.add_question(fieldname="budget", depends_on=condition("tier", "=", tier.name))

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_valid_conditions_save(self):
		tier = SponsorshipTierFactory.create(event=self.event.name)
		self.add_question(fieldname="budget", depends_on=condition("tier", "=", tier.name))
		self.add_question(fieldname="spend", mandatory_depends_on=condition("budget", ">", 5000))

		self.form.save()

		self.assertEqual(len(self.form.questions), 2)

	def add_question(self, **question):
		self.form.append(
			"questions",
			{"label": "Budget", "fieldtype": "Number", "enabled": 1, **question},
		)


def condition(fieldname: str, operator: str, value) -> str:
	return json.dumps([[fieldname, operator, value]])


class TestFormTypes(IntegrationTestCase):
	def test_an_unmapped_doctype_gets_the_default_type(self):
		default = form_type("Buzz Tag")

		self.assertIsInstance(default, FormType)
		self.assertFalse(default.one_per_event)

	def test_sponsorship_forms_are_one_per_event(self):
		self.assertTrue(form_type("Sponsorship Enquiry").one_per_event)

	def test_talk_proposal_forms_are_one_per_event(self):
		self.assertTrue(form_type("Talk Proposal").one_per_event)

	def test_registration_forms_are_one_per_event_without_a_page(self):
		registration = form_type("Event Booking")

		self.assertTrue(registration.one_per_event)
		self.assertFalse(registration.has_page)

	def test_other_custom_forms_may_repeat(self):
		self.assertFalse(form_type("Event Feedback").one_per_event)


class TestRegistrationForm(IntegrationTestCase):
	def setUp(self):
		self.event = BuzzEventFactory.create()
		self.form = frappe.get_doc("Buzz Form", {"event": self.event.name, "form_doctype": "Event Booking"})

	def test_every_event_starts_with_a_published_registration_form(self):
		self.assertEqual(self.form.route, "register")
		self.assertTrue(self.form.publish)

	def test_a_new_registration_form_starts_closed(self):
		self.assertTrue(self.form.auto_close_at)
		self.assertTrue(self.form.is_closed)

	def test_closing_registration_keeps_the_form_published(self):
		self.assertFalse(self.form.set_closed(False))
		self.assertIsNone(self.form.auto_close_at)

		self.assertTrue(self.form.set_closed(True))
		self.assertTrue(self.form.publish)

	def test_a_second_registration_form_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			BuzzFormFactory.create(event=self.event.name, form_doctype="Event Booking", route="register-2")

	def test_a_booking_and_an_attendee_question_may_share_a_fieldname(self):
		self.add_question(asked_per="Booking", fieldname="company")
		self.add_question(asked_per="Attendee", fieldname="company")

		self.form.save()

		self.assertEqual([question.fieldname for question in self.form.questions], ["company", "company"])

	def test_two_questions_of_one_kind_may_not_share_a_fieldname(self):
		self.add_question(asked_per="Booking", fieldname="company")
		self.add_question(asked_per="Booking", fieldname="company")

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_an_attendee_question_may_show_for_a_ticket_type(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event.name)
		self.add_question(
			asked_per="Attendee",
			fieldname="diet",
			depends_on=condition("ticket_type", "in", [ticket_type.name]),
		)

		self.form.save()

		self.assertEqual(len(self.form.questions), 1)

	def test_a_booking_question_may_not_name_a_ticket_type(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event.name)
		self.add_question(
			asked_per="Booking",
			fieldname="diet",
			depends_on=condition("ticket_type", "in", [ticket_type.name]),
		)

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def test_a_ticket_type_of_another_event_is_refused(self):
		foreign_ticket_type = EventTicketTypeFactory.create()
		self.add_question(
			asked_per="Attendee",
			fieldname="diet",
			depends_on=condition("ticket_type", "in", [foreign_ticket_type.name]),
		)

		with self.assertRaises(frappe.ValidationError):
			self.form.save()

	def add_question(self, **question):
		self.form.append(
			"questions",
			{"label": "Question", "fieldtype": "Data", "enabled": 1, "asked_per": "Attendee", **question},
		)
