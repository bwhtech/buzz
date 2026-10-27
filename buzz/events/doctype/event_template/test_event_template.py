# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from buzz.events.doctype.buzz_event.buzz_event import create_from_template
from buzz.events.doctype.event_template.event_template import event_template_questions
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	EventCategoryFactory,
	EventHostFactory,
	EventTemplateFactory,
	EventTicketTypeFactory,
)

DIRECT_FIELDS = {
	"medium": "Online",
	"about": "About text",
	"short_description": "Short desc",
	"time_zone": "Asia/Kolkata",
	"allow_guest_booking": 1,
	"guest_verification_method": "Email OTP",
	"send_ticket_email": 1,
	"apply_tax": 1,
	"tax_label": "GST",
	"tax_percentage": 18,
}
SPONSORSHIP_FIELDS = {
	"auto_send_pitch_deck": 1,
	"sponsor_deck_reply_to": "test@example.com",
	"sponsor_deck_cc": "cc@example.com",
}
CUSTOM_FIELD = {
	"label": "Company",
	"fieldname": "company",
	"fieldtype": "Data",
	"form_doctype": "Event Booking",
	"mandatory": 1,
	"enabled": 1,
	"placeholder": "Enter company name",
}


def form_questions(event: str) -> list[str]:
	forms = frappe.get_all("Buzz Form", filters={"event": event}, pluck="name")
	return frappe.get_all(
		"Buzz Form Field", {"parenttype": "Buzz Form", "parent": ["in", forms]}, pluck="name"
	)


class TestCreateEventFromTemplate(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.team = BuzzTeamFactory.create_owned_by().name
		cls.category = EventCategoryFactory.create().name
		cls.host = EventHostFactory.create(team=cls.team).name

	def test_copies_direct_fields(self):
		template = self.create_template(**DIRECT_FIELDS)

		event = self.create_event(template, dict.fromkeys(["category", "host", *DIRECT_FIELDS], 1))

		self.assertEqual((event.category, event.host), (self.category, self.host))
		for field, value in DIRECT_FIELDS.items():
			with self.subTest(field):
				self.assertEqual(event.get(field), value)

	def test_respects_unselected_options(self):
		template = self.create_template(medium="In Person", about="Should not appear", apply_tax=1)

		event = self.create_event(
			template, {"category": 1, "host": 1, "medium": 0, "about": 0, "apply_tax": 0}
		)

		self.assertEqual((event.category, event.host), (self.category, self.host))
		self.assertFalse(event.about)
		self.assertFalse(event.apply_tax)

	def test_additional_fields_override_the_template(self):
		category = EventCategoryFactory.create().name
		template = self.create_template()

		event = self.create_event(template, {"host": 1}, category=category)

		self.assertEqual((event.category, event.host), (category, self.host))

	def test_creates_ticket_types(self):
		early_bird = {
			"title": "Early Bird",
			"price": 500,
			"currency": "INR",
			"max_tickets_available": 100,
			"is_published": 1,
		}
		regular = {"title": "Regular", "price": 1000, "currency": "INR", "is_published": 1}
		template = self.create_template(template_ticket_types=[early_bird, regular])

		event = self.create_event(template, {"category": 1, "host": 1, "ticket_types": 1})

		ticket_types = frappe.get_all(
			"Event Ticket Type",
			filters={"event": event.name, "title": ["in", ["Early Bird", "Regular"]]},
			fields=["name", "title", {"prices": ["price"]}, "max_tickets_available"],
			order_by="title",
		)
		self.assertEqual(
			[(row.title, row.prices[0].price) for row in ticket_types],
			[("Early Bird", 500), ("Regular", 1000)],
		)
		self.assertEqual(ticket_types[0].max_tickets_available, 100)

	def test_creates_ticket_categories_and_links_ticket_types(self):
		template = self.create_template(
			template_ticket_categories=[{"title": "Workshops", "description": "Hands-on", "sort_order": 2}],
			template_ticket_types=[
				{"title": "Lab", "category": "Workshops", "price": 0, "currency": "INR", "is_published": 1}
			],
		)

		event = self.create_event(template, {"category": 1, "host": 1, "ticket_types": 1})

		category = frappe.get_value(
			"Event Ticket Category", {"event": event.name}, ["name", "title", "sort_order"], as_dict=True
		)
		self.assertEqual((category.title, category.sort_order), ("Workshops", 2))
		lab = frappe.get_value("Event Ticket Type", {"event": event.name, "title": "Lab"}, "category")
		self.assertEqual(lab, category.name)

	def test_creates_add_ons(self):
		add_on = {"title": "Workshop Access", "price": 2000, "currency": "INR", "enabled": 1}
		template = self.create_template(
			template_add_ons=[{**add_on, "user_selects_option": 1, "options": "Morning\nAfternoon"}]
		)

		event = self.create_event(template, {"category": 1, "host": 1, "add_ons": 1})

		add_ons = frappe.get_all(
			"Ticket Add-on",
			filters={"event": event.name},
			fields=["title", "price", "user_selects_option", "options"],
		)
		self.assertEqual(
			[(row.title, row.price, row.user_selects_option, row.options) for row in add_ons],
			[("Workshop Access", 2000, 1, "Morning\nAfternoon")],
		)

	def test_copies_registration_questions_onto_the_new_events_form(self):
		template = self.create_template(template_custom_fields=[CUSTOM_FIELD])

		event = self.create_event(template, {"category": 1, "host": 1, "custom_fields": 1})

		form = frappe.get_doc("Buzz Form", {"event": event.name, "form_doctype": "Event Booking"})
		self.assertEqual(
			[
				(
					question.label,
					question.fieldtype,
					question.mandatory,
					question.placeholder,
				)
				for question in form.questions
			],
			[("Company", "Data", 1, "Enter company name")],
		)

	def test_copies_form_questions_onto_the_new_events_form(self):
		template = self.create_template(
			template_custom_fields=[
				{
					**CUSTOM_FIELD,
					"label": "Dietary Preference",
					"fieldname": "dietary_preference",
					"mandatory": 0,
					"placeholder": "",
					"form_doctype": "Event Feedback",
				}
			]
		)

		event = self.create_event(template, {"category": 1, "host": 1, "custom_fields": 1})

		form = frappe.get_doc("Buzz Form", {"event": event.name, "form_doctype": "Event Feedback"})
		self.assertEqual([question.label for question in form.questions], ["Dietary Preference"])

	def test_drops_conditions_that_name_another_events_records(self):
		"""A ticket type belongs to the template's source event; a question-to-question condition travels."""
		source_ticket_type = EventTicketTypeFactory.create().name
		ticket_condition = [["ticket_type", "in", [source_ticket_type]]]
		answer_condition = [["company", "is", "set"]]
		template = self.create_template(
			template_custom_fields=[
				{**CUSTOM_FIELD, "form_doctype": "Event Booking Attendee"},
				{
					**CUSTOM_FIELD,
					"label": "Role",
					"fieldname": "role",
					"form_doctype": "Event Booking Attendee",
					"depends_on": frappe.as_json(ticket_condition + answer_condition),
				},
			]
		)

		event = self.create_event(template, {"category": 1, "host": 1, "custom_fields": 1})

		form = frappe.get_doc("Buzz Form", {"event": event.name, "form_doctype": "Event Booking Attendee"})
		self.assertEqual(frappe.parse_json(form.questions[1].depends_on), answer_condition)

	def test_skips_form_questions_for_a_form_the_event_has_not(self):
		template = self.create_template(template_custom_fields=[{**CUSTOM_FIELD, "form_doctype": "Buzz Tag"}])

		event = self.create_event(template, {"category": 1, "host": 1, "custom_fields": 1})

		self.assertFalse(form_questions(event.name))

	def test_skips_linked_docs_when_unselected(self):
		template = self.create_template(
			template_ticket_types=[{"title": "Skipped", "price": 100, "currency": "INR"}],
			template_add_ons=[{"title": "Skipped Addon", "price": 50, "currency": "INR", "enabled": 1}],
			template_custom_fields=[CUSTOM_FIELD],
		)
		options = {"category": 1, "host": 1, "ticket_types": 0, "add_ons": 0, "custom_fields": 0}

		event = self.create_event(template, options)

		self.assertFalse(frappe.db.exists("Event Ticket Type", {"event": event.name, "title": "Skipped"}))
		self.assertFalse(frappe.db.exists("Ticket Add-on", {"event": event.name}))
		self.assertFalse(form_questions(event.name))

	def test_sets_default_title_and_date(self):
		template_name = f"Defaults Template {frappe.generate_hash(length=6)}"
		template = self.create_template(template_name=template_name)

		event = self.create_event(template, {"category": 1, "host": 1})

		self.assertIn(template_name, event.title)
		self.assertEqual(str(event.start_date), today())

	def test_copies_sponsorship_settings(self):
		template = self.create_template(**SPONSORSHIP_FIELDS)

		event = self.create_event(template, dict.fromkeys(["category", "host", *SPONSORSHIP_FIELDS], 1))

		for field, value in SPONSORSHIP_FIELDS.items():
			with self.subTest(field):
				self.assertEqual(event.get(field), value)

	def test_requires_template_read_permission(self):
		template = self.create_template()

		with self.set_user("Guest"), self.assertRaises(frappe.ValidationError):
			create_from_template(template.name, frappe.as_json({"category": 1, "host": 1}))

	def create_template(self, **fields):
		return EventTemplateFactory.create(team=self.team, category=self.category, host=self.host, **fields)

	def create_event(self, template, options: dict, **additional_fields):
		# Team is not a template option; without it the event takes the user's team.
		additional_fields = frappe.as_json({"team": self.team, **additional_fields})
		return frappe.get_doc(
			"Buzz Event", create_from_template(template.name, frappe.as_json(options), additional_fields)
		)


class TestTemplateFormQuestions(IntegrationTestCase):
	"""The save side of the copy: every question of the event's forms becomes a template row."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.team = BuzzTeamFactory.create_owned_by().name

	def setUp(self):
		self.event = BuzzEventFactory.create(team=self.team)

	def test_form_questions_name_their_form(self):
		self.add_question("Event Feedback", "Dietary", "dietary")

		rows = event_template_questions(str(self.event.name))

		self.assertEqual(
			[(row["fieldname"], row["form_doctype"]) for row in rows],
			[("dietary", "Event Feedback")],
		)

	def test_registration_questions_name_their_form(self):
		self.add_question("Event Booking", "Company", "company")
		self.add_question("Event Booking Attendee", "Diet", "diet")

		rows = event_template_questions(str(self.event.name))

		self.assertCountEqual(
			[(row["fieldname"], row["form_doctype"]) for row in rows],
			[("company", "Event Booking"), ("diet", "Event Booking Attendee")],
		)

	def test_sponsorship_questions_stay_out(self):
		self.add_question("Sponsorship Enquiry", "Extra", "extra")

		self.assertEqual(event_template_questions(str(self.event.name)), [])

	def add_question(self, form_doctype: str, label: str, fieldname: str):
		form = frappe.get_doc("Buzz Form", {"event": self.event.name, "form_doctype": form_doctype})
		form.append(
			"questions",
			{
				"label": label,
				"fieldname": fieldname,
				"fieldtype": "Data",
				"enabled": 1,
			},
		)
		form.save(ignore_permissions=True)
