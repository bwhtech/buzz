import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_event.buzz_event import create_from_template
from buzz.events.doctype.event_template.event_template import create_template_from_event
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzFormFactory,
	EventTicketCategoryFactory,
	EventTicketTypeFactory,
	TicketAddOnFactory,
)

EVENT_FIELDS = {
	"medium": "Online",
	"about": "Full event description",
	"tax_label": "GST",
	"tax_percentage": 18,
}
ALL_OPTIONS = dict.fromkeys(["category", "host", "apply_tax", "ticket_types", *EVENT_FIELDS], 1)


class TestSaveEventAsTemplate(IntegrationTestCase):
	def test_saves_every_selected_option(self):
		event = self.create_event_with_linked_docs()

		template = self.save_as_template(event, {**ALL_OPTIONS, "add_ons": 1, "custom_fields": 1})

		self.assertEqual((template.category, template.host), (event.category, event.host))
		self.assertEqual(template.apply_tax, 1)
		for field, value in EVENT_FIELDS.items():
			with self.subTest(field):
				self.assertEqual(template.get(field), value)
		# The event's default "Normal" ticket type is saved too.
		self.assertEqual([row.price for row in template.template_ticket_types if row.title == "Gold"], [5000])
		self.assertEqual([row.title for row in template.template_add_ons], ["Parking"])
		self.assertEqual(
			[(row.label, row.form_doctype, row.asked_per) for row in template.template_custom_fields],
			[("Designation", "Event Booking", "Booking")],
		)

	def test_saves_only_the_selected_options(self):
		event = BuzzEventFactory.create(medium="In Person", about="Included", apply_tax=1, tax_percentage=18)

		template = self.save_as_template(event, {"category": 1, "about": 1, "medium": 0, "apply_tax": 0})

		self.assertEqual((template.category, template.about), (event.category, "Included"))
		self.assertFalse(template.host)
		self.assertFalse(template.apply_tax)

	def test_round_trip_preserves_data(self):
		original = BuzzEventFactory.create(apply_tax=1, **{**EVENT_FIELDS, "tax_label": "Service Tax"})
		platinum = {"title": "Platinum", "prices": [{"currency": "INR", "price": 10000}]}
		EventTicketTypeFactory.create(event=original.name, max_tickets_available=25, **platinum)

		template = self.save_as_template(original, ALL_OPTIONS)
		team = frappe.as_json({"team": original.team})
		new_event = create_from_template(template.name, frappe.as_json(ALL_OPTIONS), team)

		copied = frappe.get_doc("Buzz Event", new_event)
		for field in ("category", "host", "medium", "about", "tax_label", "tax_percentage"):
			with self.subTest(field):
				self.assertEqual(copied.get(field), original.get(field))
		self.assertEqual(self.ticket_type_values(new_event, "Platinum"), [(10000, 25)])

	def test_round_trip_keeps_ticket_categories(self):
		original = BuzzEventFactory.create()
		workshops = EventTicketCategoryFactory.create(
			event=original.name, title="Workshops", description="Hands-on", sort_order=3
		)
		EventTicketTypeFactory.create(event=original.name, title="Lab", category=workshops.name)

		options = {"category": 1, "ticket_types": 1}
		template = self.save_as_template(original, options)
		team = frappe.as_json({"team": original.team})
		new_event = create_from_template(template.name, frappe.as_json(options), team)

		category = frappe.get_value(
			"Event Ticket Category",
			{"event": new_event},
			["name", "title", "description", "sort_order"],
			as_dict=True,
		)
		self.assertEqual(
			(category.title, category.description, category.sort_order), ("Workshops", "Hands-on", 3)
		)
		lab = frappe.get_value("Event Ticket Type", {"event": new_event, "title": "Lab"}, "category")
		self.assertEqual(lab, category.name)

	def test_requires_template_create_permission(self):
		event = BuzzEventFactory.create()

		with self.set_user("Guest"), self.assertRaises(frappe.ValidationError):
			self.save_as_template(event, {"category": 1})

	def create_event_with_linked_docs(self):
		event = BuzzEventFactory.create(apply_tax=1, **EVENT_FIELDS)
		EventTicketTypeFactory.create(
			event=event.name, title="Gold", prices=[{"currency": "INR", "price": 5000}]
		)
		TicketAddOnFactory.create(event=event.name, title="Parking", price=200)
		BuzzFormFactory.add_question(
			event.name, label="Designation", fieldname="designation", asked_per="Booking"
		)
		return event

	def save_as_template(self, event, options: dict):
		# The event's team is not copied: the template takes Administrator's sole team.
		name = f"Saved Template {frappe.generate_hash(length=6)}"
		return frappe.get_doc(
			"Event Template", create_template_from_event(str(event.name), name, frappe.as_json(options))
		)

	def ticket_type_values(self, event: str, title: str) -> list[tuple]:
		ticket_types = frappe.get_all(
			"Event Ticket Type",
			filters={"event": event, "title": title},
			fields=["name", {"prices": ["price"]}, "max_tickets_available"],
		)
		return [(row.prices[0].price, row.max_tickets_available) for row in ticket_types]
