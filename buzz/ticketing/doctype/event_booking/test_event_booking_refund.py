# Copyright (c) 2026, BWH Studios and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from buzz.api.checkin import checkin_ticket, validate_ticket_for_checkin
from buzz.api.exceptions import Conflict
from buzz.tests.base_test_cases import CHARGED_PER_TICKET, BookingRefundTestCase
from buzz.tests.factories import BuzzEventFactory, PaymentGatewayFactory


class TestRefundSummary(BookingRefundTestCase):
	def test_each_ticket_carries_its_share_of_the_charged_total(self):
		summary = self.booking.get_refund_summary()

		self.assertEqual([ticket["amount"] for ticket in summary["tickets"]], [550.0, 550.0])

	def test_tickets_are_named_and_linked_to_their_attendee(self):
		summary = self.booking.get_refund_summary()

		self.assertTrue(all(ticket["ticket"] for ticket in summary["tickets"]))
		self.assertEqual(sorted(ticket["attendee"] for ticket in summary["tickets"]), ["Jenny", "John"])

	def test_the_whole_total_is_refundable_before_any_refund(self):
		summary = self.booking.get_refund_summary()

		self.assertEqual(summary["committed"], 0)
		self.assertEqual(summary["remaining"], 1100)

	def test_a_checked_in_ticket_is_not_offered(self):
		checked_in_ticket = self.refundable_tickets()[0]
		checkin_ticket(checked_in_ticket)

		self.assertEqual(len(self.refundable_tickets()), 1)
		self.assertNotIn(checked_in_ticket, self.refundable_tickets())


class TestBookingRefund(BookingRefundTestCase):
	def test_refund_is_refused_when_the_gateway_is_not_razorpay(self):
		self.make_payment(gateway=PaymentGatewayFactory.create().name)

		with self.assertRaises(frappe.ValidationError) as raised:
			self.booking.refund(amount=100)

		self.assertIn("Razorpay", str(raised.exception))

	def test_refund_is_refused_without_a_received_payment(self):
		self.assertRaises(frappe.ValidationError, self.booking.refund, amount=100)

	def test_refunding_tickets_records_the_refund_and_marks_it_initiated(self):
		self.make_payment()

		client = self.initiate_refund(CHARGED_PER_TICKET, tickets=self.refundable_tickets()[:1])

		client.refund_payment.assert_called_once_with(self.payment.payment_id, CHARGED_PER_TICKET)
		self.assertEqual(self.booking.refund_status, "Refund Initiated")
		refund = self.refunds()[0]
		self.assertEqual(
			(refund.refund_id, refund.status, refund.amount), (self.refund_id(), "Initiated", 550)
		)

	def test_an_unsettled_refund_cancels_nothing_yet(self):
		# A refund can still fail, so tickets are only cancelled once it settles.
		self.make_payment()
		ticket = self.refundable_tickets()[0]

		self.initiate_refund(CHARGED_PER_TICKET, tickets=[ticket])

		self.assertIsNone(self.refunds()[0].cancellation_request)
		self.assertEqual(self.cancellation_requests(), [])
		self.assertEqual([row.ticket for row in self.refunds()[0].tickets], [ticket])

	def test_a_ticket_from_another_booking_is_refused(self):
		self.make_payment()
		other_booking = self.create_paid_booking(("Stranger",), self.ticket_types[:1])
		foreign_ticket = frappe.db.get_value("Event Ticket", {"booking": other_booking.name}, "name")

		# The gateway is patched, so only the ownership check can refuse this.
		with self.assertRaises(frappe.ValidationError):
			self.initiate_refund(CHARGED_PER_TICKET, tickets=[foreign_ticket])

		self.assertEqual(self.cancellation_requests(), [])
		self.assertEqual(frappe.db.get_value("Event Ticket", foreign_ticket, "docstatus"), 1)

	def test_a_ticket_that_has_been_checked_in_is_refused(self):
		self.make_payment()
		ticket = self.refundable_tickets()[0]
		checkin_ticket(ticket)

		with self.assertRaises(frappe.ValidationError) as raised:
			self.initiate_refund(CHARGED_PER_TICKET, tickets=[ticket])

		self.assertIn("checked in", str(raised.exception))
		self.assertEqual(self.refunds(), [])

	def test_a_ticket_a_refund_holds_cannot_be_checked_in(self):
		self.make_payment()
		ticket = self.refundable_tickets()[0]
		self.initiate_refund(CHARGED_PER_TICKET, tickets=[ticket])

		with self.assertRaises(Conflict):
			validate_ticket_for_checkin(str(ticket))

		self.assertEqual(frappe.local.message_log[-1]["title"], "Ticket Refunded")

	def test_a_custom_amount_refund_cancels_no_tickets(self):
		self.make_payment()

		self.initiate_refund(100)

		self.assertIsNone(self.refunds()[0].cancellation_request)
		self.assertEqual(self.cancellation_requests(), [])


class TestRefundCeiling(BookingRefundTestCase):
	ticket_prices = (2000, 3000)
	attendee_names = ("Cheap", "Pricey")

	@classmethod
	def create_event(cls) -> str:
		return BuzzEventFactory.create().name

	def setUp(self):
		super().setUp()
		self.make_payment()

	def test_the_booking_total_is_the_ceiling(self):
		self.assertEqual(self.booking.total_amount, 5000)

	def test_a_second_refund_cannot_exceed_what_is_left_after_a_settled_one(self):
		self.initiate_refund(3000)
		self.settle_refund(self.refund_id(), 3000)

		with self.assertRaises(frappe.ValidationError) as raised:
			self.initiate_refund(3000, refund_id=self.refund_id("2"))

		self.assertIn("2,000", str(raised.exception))

	def test_a_second_refund_cannot_exceed_what_is_left_while_the_first_is_still_initiated(self):
		self.initiate_refund(3000)

		with self.assertRaises(frappe.ValidationError):
			self.initiate_refund(3000, refund_id=self.refund_id("2"))

	def test_a_failed_refund_frees_its_amount_again(self):
		self.initiate_refund(3000)
		self.fail_refund(self.refund_id(), 3000)

		self.initiate_refund(3000, refund_id=self.refund_id("2"))

		self.assertEqual(len(self.refunds()), 2)

	def test_refunding_exactly_what_is_left_is_allowed(self):
		self.initiate_refund(3000)
		self.settle_refund(self.refund_id(), 3000)

		self.initiate_refund(2000, refund_id=self.refund_id("2"))
		self.settle_refund(self.refund_id("2"), 2000)

		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual(self.booking.refunded_amount, 5000)

	def test_a_ticket_already_refunded_is_not_offered_again(self):
		low_price_ticket, high_price_ticket = self.refundable_tickets()
		self.initiate_refund(3000, tickets=[high_price_ticket])
		self.settle_refund(self.refund_id(), 3000)

		self.assertEqual(self.refundable_tickets(), [low_price_ticket])
		self.assertEqual(self.booking.get_refund_summary()["remaining"], 2000)

	def test_a_ticket_whose_refund_failed_is_offered_again(self):
		high_price_ticket = self.refundable_tickets()[1]
		self.initiate_refund(3000, tickets=[high_price_ticket])

		self.fail_refund(self.refund_id(), 3000)

		self.assertEqual(len(self.refundable_tickets()), 2)

	def settle_refund(self, refund_id: str, amount: float) -> None:
		with patch("frappe.sendmail"):
			self.apply_gateway_status(refund_id, "processed", amount)

	def fail_refund(self, refund_id: str, amount: float) -> None:
		self.apply_gateway_status(refund_id, "failed", amount)

	def apply_gateway_status(self, refund_id: str, status: str, amount: float) -> None:
		refund = frappe.get_doc("Event Booking Refund", {"refund_id": refund_id})
		refund.apply_gateway_status(status, amount)
		self.booking.reload()
