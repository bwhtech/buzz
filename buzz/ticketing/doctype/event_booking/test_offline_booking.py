import frappe

from buzz.api.booking import process_booking
from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import (
	BuzzCouponCodeFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
	OfflinePaymentMethodFactory,
)

TICKET_PRICE = 500
AWAITING_VERIFICATION = {"status": "Approval Pending", "payment_status": "Verification Pending"}


class TestOfflineBooking(BookingTestCase):
	def setUp(self):
		super().setUp()
		self.set_event({"apply_tax": 0})
		self.paid_ticket_type = EventTicketTypeFactory.create(
			event=self.event.name, prices=[{"currency": "INR", "price": TICKET_PRICE}]
		).name

	def test_offline_booking_cannot_be_submitted_directly(self):
		booking = self.create_offline_booking()

		with self.assertRaises(frappe.ValidationError):
			booking.submit()

	def test_booking_without_a_payment_method_takes_the_normal_flow(self):
		booking = self.create_booking()

		booking.submit()

		self.assertEqual(booking.payment_status, "Unpaid")

	def test_approving_submits_the_booking_and_issues_tickets(self):
		booking = self.create_offline_booking(**AWAITING_VERIFICATION)
		self.assertEqual((booking.docstatus, self.ticket_count(booking.name)), (0, 0))

		booking.approve_booking()
		booking.reload()

		self.assertEqual((booking.docstatus, booking.status, booking.payment_status), (1, "Approved", "Paid"))
		self.assertEqual(self.ticket_count(booking.name), 1)

	def test_rejecting_discards_the_booking_without_tickets(self):
		booking = self.create_offline_booking(**AWAITING_VERIFICATION)

		booking.reject_booking()
		booking.reload()

		self.assertEqual((booking.docstatus, booking.status), (2, "Rejected"))
		self.assertEqual(self.ticket_count(booking.name), 0)

	def test_offline_booking_applies_a_coupon(self):
		coupon = BuzzCouponCodeFactory.create(discount_type="Percentage", discount_value=10).name

		booking = self.create_offline_booking(coupon_code=coupon)

		self.assertEqual((booking.net_amount, booking.discount_amount, booking.total_amount), (500, 50, 450))

	def test_offline_booking_applies_tax(self):
		self.set_event({"apply_tax": 1, "tax_inclusive": 0, "tax_label": "GST", "tax_percentage": 18})

		booking = self.create_offline_booking()

		self.assertEqual((booking.net_amount, booking.tax_percentage), (500, 18))
		self.assertEqual((booking.tax_amount, booking.total_amount), (90, 590))

	def test_process_booking_leaves_an_offline_booking_in_draft(self):
		payload = self.book_offline()

		self.assertTrue(payload.offline_payment)
		booking = frappe.get_doc("Event Booking", payload.booking_name)
		self.assertEqual(booking.docstatus, 0)
		self.assertEqual((booking.status, booking.payment_status), tuple(AWAITING_VERIFICATION.values()))
		self.assertEqual(self.ticket_count(booking.name), 0)

	def test_approving_a_booking_from_process_booking_issues_tickets(self):
		booking = frappe.get_doc("Event Booking", self.book_offline().booking_name)

		booking.approve_booking()
		booking.reload()

		self.assertEqual((booking.docstatus, booking.status, booking.payment_status), (1, "Approved", "Paid"))
		self.assertEqual(self.ticket_count(booking.name), 1)

	def create_booking(self, **overrides):
		attendees = [
			{"ticket_type": self.paid_ticket_type, "first_name": "Test", "email": "test@example.com"}
		]
		return EventBookingFactory.create(event=self.event.name, attendees=attendees, **overrides)

	def create_offline_booking(self, **overrides):
		return self.create_booking(payment_method="Offline", **overrides)

	def book_offline(self):
		method = str(OfflinePaymentMethodFactory.create(event=self.event.name).name)
		attendees = [
			{
				"first_name": "Offline",
				"email": "offline@example.com",
				"ticket_type": str(self.paid_ticket_type),
			}
		]
		request = self.booking_request(attendees=attendees, is_offline=True, offline_payment_method=method)
		return process_booking(request)

	def ticket_count(self, booking: str) -> int:
		return frappe.db.count("Event Ticket", {"booking": booking})
