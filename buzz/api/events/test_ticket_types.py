from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events import get_event_ticket_types
from buzz.api.events.exceptions import CannotManageEvent
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
	PaymentGatewayFactory,
	UserFactory,
)
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import PAID_EVENTS_FLAG


class TicketTypesTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("ticket-types-owner@example.com").name
		cls.viewer = UserFactory.create_once("ticket-types-viewer@example.com").name
		cls.outsider = UserFactory.create_once("ticket-types-stranger@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.viewer, team_role="Viewer")

	def setUp(self):
		self.event = str(BuzzEventFactory.create(team=self.team).name)
		self.ticket_type = str(
			EventTicketTypeFactory.create(
				event=self.event, prices=[{"currency": "INR", "price": 1000}], max_tickets_available=200
			).name
		)

	def create_booking(self, currency="INR", attendees=1, payment_status="Paid", ticket_type=None):
		attendee = {"ticket_type": ticket_type or self.ticket_type, "first_name": "Buyer"}
		booking = EventBookingFactory.create(
			event=self.event,
			currency=currency,
			payment_status=payment_status,
			attendees=[{**attendee, "email": f"buyer-{index}@example.com"} for index in range(attendees)],
		)
		booking.submit()
		return booking

	def add_usd_price(self):
		ticket_type = frappe.get_doc("Event Ticket Type", self.ticket_type)
		ticket_type.append("prices", {"currency": "USD", "price": 15})
		ticket_type.save(ignore_permissions=True)

	def payload_as(self, user: str) -> dict:
		with self.set_user(user):
			return get_event_ticket_types(self.event).__json__()

	def revenue(self) -> dict:
		return {row["currency"]: row for row in self.payload_as(self.owner)["revenue"]}

	def ticket_type_row(self, payload: dict) -> dict:
		return next(row for row in payload["ticket_types"] if row["name"] == self.ticket_type)


class TestGetEventTicketTypes(TicketTypesTestCase):
	def test_lists_ticket_types_with_tickets_sold(self):
		self.create_booking()

		payload = self.payload_as(self.owner)

		self.assertTrue(payload["can_write"])
		row = self.ticket_type_row(payload)
		self.assertEqual(row["prices"], [{"currency": "INR", "price": 1000, "tickets_sold": 1}])
		self.assertEqual(row["max_tickets_available"], 200)
		self.assertEqual(row["tickets_sold"], 1)

	def test_reports_whether_the_team_can_sell_paid_tickets(self):
		self.assertTrue(self.payload_as(self.owner)["paid_events_enabled"])

		# The team is shared by the class, and rollback is per class.
		self.addCleanup(BuzzTeamFactory.set_settings, self.team, {PAID_EVENTS_FLAG: 1})
		BuzzTeamFactory.set_settings(self.team, {PAID_EVENTS_FLAG: 0})
		self.assertFalse(self.payload_as(self.owner)["paid_events_enabled"])

	def test_viewer_reads_without_write_access(self):
		self.assertFalse(self.payload_as(self.viewer)["can_write"])

	def test_outsider_cannot_read(self):
		with self.assertRaises(CannotManageEvent):
			self.payload_as(self.outsider)

	def test_lists_sales_per_currency(self):
		self.add_usd_price()
		self.create_booking("USD")

		row = self.ticket_type_row(self.payload_as(self.owner))

		self.assertEqual([price["tickets_sold"] for price in row["prices"]], [0, 1])

	def test_lists_payment_providers_and_flags_the_default(self):
		default = PaymentGatewayFactory.create().name

		with self.change_settings("Buzz Settings", default_payment_gateway=default):
			providers = self.payload_as(self.owner)["payment_providers"]

		self.assertEqual(providers, [{"name": default, "is_default": True}])


class TestRegistrationRevenue(TicketTypesTestCase):
	def test_totals_paid_bookings_per_currency(self):
		self.add_usd_price()
		self.create_booking(attendees=2)
		self.create_booking("USD")

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
		self.create_booking(payment_status="Unpaid")
		self.create_booking(ticket_type=EventTicketTypeFactory.create(event=self.event).name)

		self.assertEqual(self.revenue(), {})

	def test_reports_refunds_beside_the_amount_collected(self):
		booking = self.create_booking(attendees=2)
		frappe.db.set_value("Event Booking", booking.name, "refunded_amount", 1000)

		self.assertEqual(self.revenue()["INR"]["refunded"], 1000)
		self.assertEqual(self.revenue()["INR"]["collected"], 2000)

	# Cancelling a ticket mails the holder, and CI has no outgoing email account.
	@patch("buzz.ticketing.doctype.event_ticket.event_ticket.send_message_email")
	def test_counts_only_tickets_still_held(self, _send_message_email):
		booking = self.create_booking(attendees=2)
		ticket = frappe.get_all("Event Ticket", filters={"booking": booking.name}, pluck="name")[0]
		frappe.get_doc("Event Ticket", ticket).cancel()

		self.assertEqual(self.revenue()["INR"]["tickets"], 1)
