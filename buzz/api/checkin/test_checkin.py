import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.checkin import checkin_ticket, validate_ticket_for_checkin
from buzz.api.checkin.exceptions import AlreadyCheckedIn, TicketCancelled, TicketNotFound

TICKET_FIELDS = {
	"id",
	"attendee_name",
	"attendee_email",
	"event_title",
	"ticket_type",
	"venue",
	"start_date",
	"start_time",
	"end_date",
	"end_time",
	"is_checked_in",
	"check_in_time",
	"check_in_date",
	"booking_id",
	"add_ons",
}


class CheckinTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = frappe.get_doc("Buzz Event", {"route": "test-route"}).name

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()

		self.ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.event,
				"title": f"Checkin Test {frappe.generate_hash(length=6)}",
				"price": 0,
			}
		).insert()

		self.ticket = frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"event": self.event,
				"ticket_type": self.ticket_type.name,
				"attendee_name": "Scanned Attendee",
				"attendee_email": "scanned@example.com",
			}
		).insert()

	def make_booked_ticket(self) -> str:
		"""Book the ticket type and pay for it, and return the ticket that came out."""
		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event,
				"user": "Administrator",
				"attendees": [
					{
						"ticket_type": self.ticket_type.name,
						"first_name": "Booked",
						"email": "booked@example.com",
					}
				],
			}
		).insert()
		booking.payment_status = "Paid"
		booking.submit()

		frappe.get_doc(
			{
				"doctype": "Event Payment",
				"user": "Administrator",
				"amount": booking.total_amount,
				"currency": booking.currency,
				"reference_doctype": "Event Booking",
				"reference_docname": booking.name,
				"payment_received": 1,
			}
		).insert()

		return frappe.db.get_value("Event Ticket", {"booking": booking.name}, "name")

	def tearDown(self):
		frappe.db.rollback()


class TestValidateTicketForCheckin(CheckinTestCase):
	def test_unknown_ticket_raises_not_found(self):
		with self.assertRaises(TicketNotFound):
			validate_ticket_for_checkin("no-such-ticket")

		self.assertEqual(frappe.local.message_log[-1]["title"], "Ticket Not Found")

	def test_status_codes(self):
		self.assertEqual(TicketNotFound.http_status_code, 404)
		self.assertEqual(TicketCancelled.http_status_code, 409)
		self.assertEqual(AlreadyCheckedIn.http_status_code, 409)

	def test_response_shape(self):
		response = validate_ticket_for_checkin(self.ticket.name).__json__()

		self.assertEqual(set(response), {"message", "ticket", "payment_details"})
		self.assertEqual(set(response["ticket"]), TICKET_FIELDS)

	def test_ticket_reads_as_not_checked_in(self):
		ticket = validate_ticket_for_checkin(self.ticket.name).__json__()["ticket"]

		self.assertEqual(ticket["id"], self.ticket.name)
		self.assertFalse(ticket["is_checked_in"])
		self.assertIsNone(ticket["check_in_time"])
		self.assertIsNone(ticket["check_in_date"])

	def test_payment_details_are_reported_for_a_paid_booking(self):
		# Event Payment is named by autoincrement, so its name arrives as an int.
		ticket = self.make_booked_ticket()

		response = validate_ticket_for_checkin(ticket).__json__()

		self.assertEqual(response["payment_details"]["amount"], 0)

	def test_cancelled_ticket_is_rejected(self):
		frappe.db.set_value("Event Ticket", self.ticket.name, "docstatus", 2)
		frappe.clear_document_cache("Event Ticket", self.ticket.name)

		with self.assertRaises(TicketCancelled):
			validate_ticket_for_checkin(self.ticket.name)


class TestCheckinTicket(CheckinTestCase):
	def test_checkin_records_and_reports(self):
		response = checkin_ticket(self.ticket.name).__json__()

		self.assertEqual(set(response["ticket"]), TICKET_FIELDS)
		self.assertTrue(response["ticket"]["is_checked_in"])
		self.assertIsNotNone(response["ticket"]["check_in_time"])
		self.assertTrue(frappe.db.exists("Event Check In", {"ticket": self.ticket.name}))

	def test_second_checkin_same_day_is_rejected(self):
		checkin_ticket(self.ticket.name)
		frappe.clear_messages()

		with self.assertRaises(AlreadyCheckedIn):
			checkin_ticket(self.ticket.name)

		self.assertIn("already checked in today", frappe.local.message_log[-1]["message"])

	def test_validation_rejects_an_already_checked_in_ticket(self):
		checkin_ticket(self.ticket.name)

		with self.assertRaises(AlreadyCheckedIn):
			validate_ticket_for_checkin(self.ticket.name)
