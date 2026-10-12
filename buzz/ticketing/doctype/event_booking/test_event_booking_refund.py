# Copyright (c) 2026, BWH Studios and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from bwh_payments import testing as payment_testing

from buzz.api.checkin import checkin_ticket, validate_ticket_for_checkin
from buzz.api.exceptions import Conflict
from buzz.tests.base_test_cases import CHARGED_PER_TICKET, BookingRefundTestCase
from buzz.tests.factories import BuzzEventFactory


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
	def test_refund_is_refused_without_a_received_payment(self):
		booking = self.create_booking(("Unpaid",), self.ticket_types[:1])
		booking.submit()

		self.assertRaises(frappe.ValidationError, booking.refund, amount=100)

	def test_refunding_tickets_records_the_refund_and_marks_it_initiated(self):
		self.initiate_refund(CHARGED_PER_TICKET, tickets=self.refundable_tickets()[:1])

		self.assertEqual(self.booking.refund_status, "Refund Initiated")
		refund = self.refunds()[0]
		self.assertEqual(
			(refund.status, refund.amount, refund.payment), ("Initiated", 550, str(self.payment.name))
		)
		gateway_refund = frappe.get_doc("Gateway Refund", refund.gateway_refund)
		self.assertEqual((gateway_refund.amount, gateway_refund.reference), (550, refund.name))
		self.assertEqual(refund.refund_id, gateway_refund.refund_id)

	def test_a_refund_the_gateway_settles_at_once_cancels_its_tickets_at_once(self):
		ticket = self.refundable_tickets()[0]
		payment_testing.set_next_refund_status("Processed")

		with patch("frappe.sendmail"):
			self.booking.refund(amount=CHARGED_PER_TICKET, tickets=[ticket])

		self.booking.reload()
		self.assertEqual(self.refunds()[0].status, "Processed")
		self.assertEqual(self.booking.refund_status, "Partially Refunded")
		self.assertEqual(frappe.db.get_value("Event Ticket", ticket, "docstatus"), 2)

	def test_refund_returns_its_own_status_not_the_bookings(self):
		payment_testing.set_next_refund_status("Processed")
		with patch("frappe.sendmail"):
			self.booking.refund(amount=CHARGED_PER_TICKET)

		payment_testing.set_next_refund_status("Pending")
		self.assertEqual(self.booking.refund(amount=CHARGED_PER_TICKET), "Initiated")

	def test_a_refund_the_gateway_refuses_is_recorded_as_failed(self):
		payment_testing.set_next_refund_status("Failed")

		with self.assertRaises(frappe.ValidationError):
			self.booking.refund(amount=CHARGED_PER_TICKET)

		self.booking.reload()
		self.assertEqual([refund.status for refund in self.refunds()], ["Failed"])
		self.assertEqual(self.booking.get_refund_summary()["remaining"], 1100)

	def test_an_unsettled_refund_cancels_nothing_yet(self):
		# A refund can still fail, so tickets are only cancelled once it settles.
		ticket = self.refundable_tickets()[0]

		self.initiate_refund(CHARGED_PER_TICKET, tickets=[ticket])

		self.assertIsNone(self.refunds()[0].cancellation_request)
		self.assertEqual(self.cancellation_requests(), [])
		self.assertEqual([row.ticket for row in self.refunds()[0].tickets], [ticket])

	def test_a_ticket_from_another_booking_is_refused(self):
		other_booking = self.create_paid_booking(("Stranger",), self.ticket_types[:1])
		foreign_ticket = frappe.db.get_value("Event Ticket", {"booking": other_booking.name}, "name")

		with self.assertRaises(frappe.ValidationError):
			self.initiate_refund(CHARGED_PER_TICKET, tickets=[foreign_ticket])

		self.assertEqual(self.cancellation_requests(), [])
		self.assertEqual(frappe.db.get_value("Event Ticket", foreign_ticket, "docstatus"), 1)

	def test_a_ticket_that_has_been_checked_in_is_refused(self):
		ticket = self.refundable_tickets()[0]
		checkin_ticket(ticket)

		with self.assertRaises(frappe.ValidationError) as raised:
			self.initiate_refund(CHARGED_PER_TICKET, tickets=[ticket])

		self.assertIn("checked in", str(raised.exception))
		self.assertEqual(self.refunds(), [])

	def test_a_ticket_a_refund_holds_cannot_be_checked_in(self):
		ticket = self.refundable_tickets()[0]
		self.initiate_refund(CHARGED_PER_TICKET, tickets=[ticket])

		with self.assertRaises(Conflict):
			validate_ticket_for_checkin(str(ticket))

		self.assertEqual(frappe.local.message_log[-1]["title"], "Ticket Refunded")

	def test_a_custom_amount_refund_cancels_no_tickets(self):
		self.initiate_refund(100)

		self.assertIsNone(self.refunds()[0].cancellation_request)
		self.assertEqual(self.cancellation_requests(), [])


class TestRefundCeiling(BookingRefundTestCase):
	ticket_prices = (2000, 3000)
	attendee_names = ("Cheap", "Pricey")

	@classmethod
	def create_event(cls) -> str:
		return BuzzEventFactory.create(payment_gateways=[{"payment_gateway": cls.gateway}]).name

	def test_the_booking_total_is_the_ceiling(self):
		self.assertEqual(self.booking.total_amount, 5000)

	def test_a_second_refund_cannot_exceed_what_is_left_after_a_settled_one(self):
		self.initiate_refund(3000)
		self.settle_refund(self.refunds()[0])

		with self.assertRaises(frappe.ValidationError) as raised:
			self.initiate_refund(3000)

		self.assertIn("2,000", str(raised.exception))

	def test_a_second_refund_cannot_exceed_what_is_left_while_the_first_is_still_initiated(self):
		self.initiate_refund(3000)

		with self.assertRaises(frappe.ValidationError):
			self.initiate_refund(3000)

	def test_a_failed_refund_frees_its_amount_again(self):
		self.initiate_refund(3000)
		self.settle_refund(self.refunds()[0], "Failed")

		self.initiate_refund(3000)

		self.assertEqual(len(self.refunds()), 2)

	def test_refunding_exactly_what_is_left_is_allowed(self):
		self.initiate_refund(3000)
		self.settle_refund(self.refunds()[0])

		self.initiate_refund(2000)
		self.settle_refund(self.refunds()[1])

		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual(self.booking.refunded_amount, 5000)

	def test_a_ticket_already_refunded_is_not_offered_again(self):
		low_price_ticket, high_price_ticket = self.refundable_tickets()
		self.initiate_refund(3000, tickets=[high_price_ticket])
		self.settle_refund(self.refunds()[0])

		self.assertEqual(self.refundable_tickets(), [low_price_ticket])
		self.assertEqual(self.booking.get_refund_summary()["remaining"], 2000)

	def test_a_ticket_whose_refund_failed_is_offered_again(self):
		high_price_ticket = self.refundable_tickets()[1]
		self.initiate_refund(3000, tickets=[high_price_ticket])

		self.settle_refund(self.refunds()[0], "Failed")

		self.assertEqual(len(self.refundable_tickets()), 2)
