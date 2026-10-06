import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.checkin import checkin_ticket, validate_ticket_for_checkin
from buzz.api.checkin.exceptions import AlreadyCheckedIn, TicketCancelled, TicketNotFound
from buzz.tests.factories import (
	BuzzEventFactory,
	EventBookingFactory,
	EventPaymentFactory,
	EventTicketFactory,
)


class CheckinTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create().name

	def setUp(self):
		frappe.clear_messages()
		self.ticket = EventTicketFactory.create(event=self.event).name

	def create_paid_ticket(self, amount: int) -> str:
		booking = EventBookingFactory.create(event=self.event, payment_status="Paid")
		booking.submit()
		EventPaymentFactory.create(
			"received",
			reference_doctype="Event Booking",
			reference_docname=booking.name,
			amount=amount,
			currency=booking.currency,
		)
		return frappe.db.get_value("Event Ticket", {"booking": booking.name}, "name")


class TestValidateTicketForCheckin(CheckinTestCase):
	def test_unknown_ticket_raises_not_found(self):
		with self.assertRaises(TicketNotFound):
			validate_ticket_for_checkin("no-such-ticket")

		self.assertEqual(frappe.local.message_log[-1]["title"], "Ticket Not Found")

	def test_ticket_reads_as_not_checked_in(self):
		ticket = validate_ticket_for_checkin(self.ticket).__json__()["ticket"]

		self.assertEqual(ticket["id"], self.ticket)
		self.assertFalse(ticket["is_checked_in"])
		self.assertIsNone(ticket["check_in_time"])
		self.assertIsNone(ticket["check_in_date"])

	def test_payment_details_are_reported_for_a_paid_booking(self):
		ticket = self.create_paid_ticket(amount=250)

		response = validate_ticket_for_checkin(ticket).__json__()

		self.assertEqual(response["payment_details"]["amount"], 250)

	def test_cancelled_ticket_is_rejected(self):
		frappe.db.set_value("Event Ticket", self.ticket, "docstatus", 2)
		frappe.clear_document_cache("Event Ticket", self.ticket)

		with self.assertRaises(TicketCancelled):
			validate_ticket_for_checkin(self.ticket)


class TestCheckinTicket(CheckinTestCase):
	def test_checkin_records_and_reports(self):
		response = checkin_ticket(self.ticket).__json__()

		self.assertTrue(response["ticket"]["is_checked_in"])
		self.assertIsNotNone(response["ticket"]["check_in_time"])
		self.assertTrue(frappe.db.exists("Event Check In", {"ticket": self.ticket}))

	def test_second_checkin_same_day_is_rejected(self):
		checkin_ticket(self.ticket)
		frappe.clear_messages()

		with self.assertRaises(AlreadyCheckedIn):
			checkin_ticket(self.ticket)

		self.assertIn("already checked in today", frappe.local.message_log[-1]["message"])

	def test_validation_rejects_an_already_checked_in_ticket(self):
		checkin_ticket(self.ticket)

		with self.assertRaises(AlreadyCheckedIn):
			validate_ticket_for_checkin(self.ticket)
