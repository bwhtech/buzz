from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events import get_event_ticket_types
from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.events.test_events import create_event
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.test_permissions import add_member


class TicketTypesTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.owner = create_user("ticket-types-owner@example.com", "Owner")
		cls.viewer = create_user("ticket-types-viewer@example.com", "Viewer")
		cls.stranger = create_user("ticket-types-stranger@example.com", "Stranger")
		cls.team = create_owned_team("Ticket Types Team", cls.owner)
		add_member(cls.team, cls.viewer, "Viewer")

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.event = create_event("Ticket Types Event", self.team)
		self.ticket_type = self.make_ticket_type("General admission", price=1000, seats=200)

	def make_ticket_type(self, title, price=0, seats=0):
		return str(
			frappe.get_doc(
				{
					"doctype": "Event Ticket Type",
					"event": self.event,
					"title": title,
					"prices": [{"currency": "INR", "price": price}],
					"max_tickets_available": seats,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def sell(self, currency="INR", attendees=1, payment_status="Paid", ticket_type=None):
		attendee = {
			"ticket_type": ticket_type or self.ticket_type,
			"first_name": "Buyer",
			"email": "buyer@example.com",
		}
		return (
			frappe.get_doc(
				{
					"doctype": "Event Booking",
					"event": self.event,
					"user": "Administrator",
					"currency": currency,
					"payment_status": payment_status,
					"attendees": [attendee] * attendees,
				}
			)
			.insert(ignore_permissions=True)
			.submit()
		)

	def add_usd_price(self):
		ticket_type = frappe.get_doc("Event Ticket Type", self.ticket_type)
		ticket_type.append("prices", {"currency": "USD", "price": 15})
		ticket_type.save(ignore_permissions=True)

	def revenue(self):
		frappe.set_user(self.owner)
		payload = get_event_ticket_types(self.event).__json__()
		return {row["currency"]: row for row in payload["revenue"]}


class TestGetEventTicketTypes(TicketTypesTestCase):
	def test_lists_ticket_types_with_tickets_sold(self):
		self.sell()
		frappe.set_user(self.owner)

		payload = get_event_ticket_types(self.event).__json__()

		self.assertTrue(payload["can_write"])
		row = next(row for row in payload["ticket_types"] if row["name"] == self.ticket_type)
		self.assertEqual(row["name"], self.ticket_type)
		self.assertEqual(row["prices"], [{"currency": "INR", "price": 1000, "tickets_sold": 1}])
		self.assertEqual(row["max_tickets_available"], 200)
		self.assertEqual(row["tickets_sold"], 1)

	def test_viewer_reads_without_write_access(self):
		frappe.set_user(self.viewer)

		payload = get_event_ticket_types(self.event).__json__()

		self.assertFalse(payload["can_write"])

	def test_stranger_cannot_read(self):
		frappe.set_user(self.stranger)

		with self.assertRaises(CannotManageEvent):
			get_event_ticket_types(self.event)

	def test_lists_sales_per_currency(self):
		self.add_usd_price()
		self.sell("USD")
		frappe.set_user(self.owner)

		payload = get_event_ticket_types(self.event).__json__()

		row = next(row for row in payload["ticket_types"] if row["name"] == self.ticket_type)
		self.assertEqual([price["tickets_sold"] for price in row["prices"]], [0, 1])

	def test_lists_payment_providers_and_flags_the_default(self):
		gateway = {"doctype": "Payment Gateway", "gateway": f"Default Gateway {frappe.generate_hash(6)}"}
		default = frappe.get_doc(gateway).insert().name
		frappe.db.set_single_value("Buzz Settings", "default_payment_gateway", default)
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")
		frappe.set_user(self.owner)

		payload = get_event_ticket_types(self.event).__json__()

		self.assertEqual(payload["payment_providers"], [{"name": default, "is_default": True}])


class TestRegistrationRevenue(TicketTypesTestCase):
	def test_totals_paid_bookings_per_currency(self):
		self.add_usd_price()
		self.sell(attendees=2)
		self.sell("USD")

		revenue = self.revenue()

		self.assertEqual(
			revenue["INR"],
			{"currency": "INR", "collected": 2000, "refunded": 0, "bookings": 1, "tickets": 2},
		)
		self.assertEqual(
			revenue["USD"],
			{"currency": "USD", "collected": 15, "refunded": 0, "bookings": 1, "tickets": 1},
		)

	def test_leaves_out_unpaid_and_free_bookings(self):
		self.sell(payment_status="Unpaid")
		self.sell(ticket_type=self.make_ticket_type("Community pass"))

		self.assertEqual(self.revenue(), {})

	def test_reports_refunds_beside_the_amount_collected(self):
		booking = self.sell(attendees=2)
		frappe.db.set_value("Event Booking", booking.name, "refunded_amount", 1000)

		self.assertEqual(self.revenue()["INR"]["refunded"], 1000)
		self.assertEqual(self.revenue()["INR"]["collected"], 2000)

	# Cancelling a ticket mails the holder, and CI has no outgoing email account.
	@patch("buzz.ticketing.doctype.event_ticket.event_ticket.send_message_email")
	def test_counts_only_tickets_still_held(self, _send_message_email):
		booking = self.sell(attendees=2)
		ticket = frappe.get_all("Event Ticket", filters={"booking": booking.name}, pluck="name")[0]
		frappe.get_doc("Event Ticket", ticket).cancel()

		self.assertEqual(self.revenue()["INR"]["tickets"], 1)
