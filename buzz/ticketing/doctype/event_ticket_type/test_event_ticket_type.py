# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, EventTicketTypeFactory
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import PAID_EVENTS_FLAG


class TestEventTicketTypePrices(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.event = frappe.db.get_value("Buzz Event", {"route": "test-route"})
		self.ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.event,
				"title": "Priced ticket",
				"prices": [{"currency": "INR", "price": 1000}, {"currency": "USD", "price": 15}],
			}
		).insert()

	def tearDown(self):
		frappe.db.rollback()

	def sell(self, currency):
		frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event,
				"user": "Administrator",
				"currency": currency,
				"payment_status": "Paid",
				"attendees": [
					{
						"ticket_type": self.ticket_type.name,
						"first_name": "Buyer",
						"email": "buyer@example.com",
					}
				],
			}
		).insert().submit()

	def save_prices(self, *prices):
		self.ticket_type.reload()
		self.ticket_type.set("prices", [{"currency": currency, "price": price} for currency, price in prices])
		self.ticket_type.save()

	def test_saved_without_prices_is_free_in_inr(self):
		ticket_type = frappe.get_doc(
			{"doctype": "Event Ticket Type", "event": self.event, "title": "Free"}
		).insert()

		self.assertEqual([(row.currency, row.price) for row in ticket_type.prices], [("INR", 0)])

	def test_price_is_locked_after_a_sale_in_its_currency(self):
		self.sell("USD")

		self.save_prices(("INR", 1200), ("USD", 15))
		with self.assertRaises(frappe.ValidationError):
			self.save_prices(("INR", 1200), ("USD", 20))
		with self.assertRaises(frappe.ValidationError):
			self.save_prices(("INR", 1200))

	def test_paid_ticket_cannot_be_free_in_another_currency(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_prices(("INR", 1000), ("USD", 0))

	def test_free_ticket_cannot_be_paid_in_another_currency(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_prices(("INR", 0), ("USD", 15))

	def test_rejects_a_currency_twice(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_prices(("INR", 1000), ("USD", 15), ("USD", 15))

	def test_ticket_type_with_sales_cannot_be_deleted(self):
		self.sell("INR")

		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("Event Ticket Type", self.ticket_type.name)


class TestPaidEventsFlag(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.event = BuzzEventFactory.create()
		self.addCleanup(frappe.clear_document_cache, "Buzz Team Settings", self.event.team)

	def set_paid_events(self, value: int):
		BuzzTeamFactory.set_settings(self.event.team, {PAID_EVENTS_FLAG: value})

	def test_free_ticket_type_saves_without_the_flag(self):
		self.set_paid_events(0)
		EventTicketTypeFactory.create(event=self.event.name)

	def test_paid_ticket_type_needs_the_flag(self):
		self.set_paid_events(0)
		with self.assertRaises(frappe.ValidationError):
			EventTicketTypeFactory.create("paid", event=self.event.name)

	def test_free_ticket_type_cannot_turn_paid_without_the_flag(self):
		self.set_paid_events(0)
		ticket_type = EventTicketTypeFactory.create(event=self.event.name)
		ticket_type.set("prices", [{"currency": "INR", "price": 500}])
		with self.assertRaises(frappe.ValidationError):
			ticket_type.save()

	def test_existing_paid_ticket_type_stays_editable_after_the_flag_is_off(self):
		ticket_type = EventTicketTypeFactory.create("paid", event=self.event.name)
		self.set_paid_events(0)

		ticket_type.title = "Renamed"
		ticket_type.is_published = 0
		ticket_type.save()

		self.assertEqual(frappe.db.get_value("Event Ticket Type", ticket_type.name, "title"), "Renamed")
