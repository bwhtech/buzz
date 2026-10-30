from unittest.mock import patch

import frappe
from bwh_payments import testing as payment_testing

from buzz.api.checkin import checkin_ticket
from buzz.tests.base_test_cases import CHARGED_PER_TICKET, BookingRefundTestCase

BOOKING_TOTAL = 1100


class TestRefundWebhooks(BookingRefundTestCase):
	def test_a_processed_refund_covering_the_total_marks_the_booking_refunded(self):
		self.initiate_refund(BOOKING_TOTAL)

		self.settle_refund(self.refunds()[0])

		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual(self.booking.refunded_amount, BOOKING_TOTAL)
		self.assertEqual(self.refunds()[0].status, "Processed")

	def test_a_processed_refund_below_the_total_marks_the_booking_partially_refunded(self):
		self.initiate_refund(CHARGED_PER_TICKET)

		self.settle_refund(self.refunds()[0])

		self.assertEqual(self.booking.refund_status, "Partially Refunded")
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)

	def test_a_full_refund_buzz_never_raised_cancels_every_remaining_ticket(self):
		# Raised on the gateway's dashboard: the webhook carries no tickets.
		self.refund_outside_buzz(BOOKING_TOTAL)

		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual(len(self.refunds()[0].tickets), 2)
		self.assertEqual([request.docstatus for request in self.cancellation_requests()], [1])

	def test_a_partial_refund_buzz_never_raised_cancels_nothing(self):
		self.refund_outside_buzz(CHARGED_PER_TICKET)

		self.assertEqual(self.refunds()[0].tickets, [])
		self.assertEqual(self.cancellation_requests(), [])

	def test_a_refund_buzz_never_raised_still_pending_is_initiated(self):
		self.refund_outside_buzz(BOOKING_TOTAL, "Pending")

		self.assertEqual(self.refunds()[0].status, "Initiated")
		self.assertEqual(self.booking.refund_status, "Refund Initiated")
		self.assertEqual(self.cancellation_requests(), [])

	def test_the_same_outcome_reported_twice_is_not_counted_twice(self):
		self.initiate_refund(CHARGED_PER_TICKET)

		self.settle_refund(self.refunds()[0])
		self.settle_refund(self.refunds()[0])

		self.assertEqual(len(self.refunds()), 1)
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)

	def test_a_failed_refund_is_not_counted_and_cancels_nothing(self):
		ticket = self.refundable_tickets()[0]
		self.initiate_refund(CHARGED_PER_TICKET, tickets=[ticket])

		self.settle_refund(self.refunds()[0], "Failed")

		self.assertEqual(self.refunds()[0].status, "Failed")
		self.assertEqual(self.booking.refunded_amount, 0)
		self.assertEqual(self.cancellation_requests(), [])
		self.assertEqual(frappe.db.get_value("Event Ticket", ticket, "docstatus"), 1)

	def test_a_webhook_delivered_as_guest_still_updates_the_booking(self):
		# The webhook is an allow_guest endpoint.
		self.initiate_refund(CHARGED_PER_TICKET, tickets=self.refundable_tickets()[:1])

		with self.set_user("Guest"):
			self.settle_refund(self.refunds()[0])

		self.assertEqual(self.refunds()[0].status, "Processed")
		self.assertEqual(self.booking.refund_status, "Partially Refunded")
		self.assertEqual([request.docstatus for request in self.cancellation_requests()], [1])

	def test_a_processed_refund_raises_and_submits_the_cancellation(self):
		ticket = self.refundable_tickets()[0]
		self.initiate_refund(CHARGED_PER_TICKET, tickets=[ticket])

		self.settle_refund(self.refunds()[0])

		request = frappe.get_doc("Ticket Cancellation Request", self.refunds()[0].cancellation_request)
		self.assertEqual((request.status, request.docstatus), ("Accepted", 1))
		self.assertEqual(frappe.db.get_value("Event Ticket", ticket, "docstatus"), 2)

	def test_a_cancellation_that_cannot_go_through_leaves_the_refund_recorded(self):
		ticket = self.refundable_tickets()[0]
		self.initiate_refund(CHARGED_PER_TICKET, tickets=[ticket])

		with patch("frappe.sendmail", side_effect=Exception("no outgoing email account")):
			payment_testing.send_refund_webhook(self.refunds()[0].gateway_refund, "Processed")

		self.booking.reload()
		self.assertEqual(self.refunds()[0].status, "Processed")
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)
		request = frappe.get_doc("Ticket Cancellation Request", self.refunds()[0].cancellation_request)
		self.assertEqual((request.status, request.docstatus), ("In Review", 0))
		self.assertEqual(frappe.db.get_value("Event Ticket", ticket, "docstatus"), 1)

	def test_a_checked_in_ticket_is_never_cancelled_by_a_refund_buzz_never_raised(self):
		checked_in_ticket, other_ticket = self.refundable_tickets()
		checkin_ticket(checked_in_ticket)

		self.refund_outside_buzz(BOOKING_TOTAL)

		self.assertEqual([row.ticket for row in self.refunds()[0].tickets], [other_ticket])

	def test_two_refunds_buzz_never_raised_cancel_the_tickets_once_they_cover_the_total(self):
		# Only the second refund brings the total up to the booking amount.
		self.refund_outside_buzz(CHARGED_PER_TICKET)
		self.refund_outside_buzz(CHARGED_PER_TICKET)

		first, second = self.refunds()
		self.assertEqual((first.tickets, len(second.tickets)), ([], 2))
		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual([request.docstatus for request in self.cancellation_requests()], [1])


class TestSyncRefunds(BookingRefundTestCase):
	def test_a_pending_refund_settles_once_the_gateway_reports_it(self):
		ticket = self.refundable_tickets()[0]
		self.initiate_refund(CHARGED_PER_TICKET, tickets=[ticket])
		payment_testing.set_refund_status(self.refunds()[0].gateway_refund, "Processed")

		result = self.sync()

		self.assertEqual(result, {"pending": 0})
		self.assertEqual(self.refunds()[0].status, "Processed")
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)
		self.assertEqual(frappe.db.get_value("Event Ticket", ticket, "docstatus"), 2)

	def test_a_refund_the_gateway_failed_frees_its_tickets(self):
		self.initiate_refund(CHARGED_PER_TICKET, tickets=self.refundable_tickets()[:1])
		payment_testing.set_refund_status(self.refunds()[0].gateway_refund, "Failed")

		self.sync()

		self.assertEqual(self.refunds()[0].status, "Failed")
		self.assertEqual(len(self.refundable_tickets()), 2)

	def test_a_refund_the_gateway_still_holds_stays_initiated(self):
		self.initiate_refund(CHARGED_PER_TICKET)

		result = self.sync()

		self.assertEqual(result, {"pending": 1})
		self.assertEqual(self.refunds()[0].status, "Initiated")

	def test_a_payment_with_no_refunds_changes_nothing(self):
		self.assertEqual(self.sync(), {"pending": 0})
		self.assertEqual(self.booking.refund_status, "")

	def test_sync_is_refused_without_a_received_payment(self):
		frappe.db.set_value("Event Payment", self.payment.name, "payment_received", 0)

		self.assertRaises(frappe.ValidationError, self.booking.sync_refunds)

	def sync(self) -> dict:
		with patch("frappe.sendmail"):
			result = self.booking.sync_refunds()
		self.booking.reload()
		return result
