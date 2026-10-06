from unittest.mock import MagicMock, patch

import frappe
from pydantic import ValidationError

from buzz.payments import handle_refund_notification
from buzz.tests.factories import PaymentGatewayFactory
from buzz.ticketing.doctype.event_booking.refund_test_case import (
	CHARGED_PER_TICKET,
	GATEWAY_CONTROLLER,
	BookingRefundTestCase,
)

BOOKING_TOTAL = 1100


class TestRefundNotification(BookingRefundTestCase):
	def setUp(self):
		super().setUp()
		self.make_payment()

	def test_a_processed_refund_covering_the_total_marks_the_booking_refunded(self):
		self.initiate(BOOKING_TOTAL)

		self.notify(self.refund_id(), "processed", BOOKING_TOTAL)

		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual(self.booking.refunded_amount, BOOKING_TOTAL)
		self.assertEqual(self.refunds()[0].status, "Processed")

	def test_a_processed_refund_below_the_total_marks_the_booking_partially_refunded(self):
		self.initiate(CHARGED_PER_TICKET)

		self.notify(self.refund_id(), "processed", CHARGED_PER_TICKET)

		self.assertEqual(self.booking.refund_status, "Partially Refunded")
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)

	def test_a_full_refund_buzz_never_raised_cancels_every_remaining_ticket(self):
		# Raised on the Razorpay dashboard: the webhook carries no tickets.
		self.notify(self.refund_id(), "processed", BOOKING_TOTAL)

		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual(len(self.refunds()[0].tickets), 2)
		self.assertEqual([request.docstatus for request in self.cancellation_requests()], [1])

	def test_a_partial_refund_buzz_never_raised_cancels_nothing(self):
		self.notify(self.refund_id(), "processed", CHARGED_PER_TICKET)

		self.assertEqual(self.refunds()[0].tickets, [])
		self.assertEqual(self.cancellation_requests(), [])

	def test_the_same_event_arriving_twice_is_not_counted_twice(self):
		self.initiate(CHARGED_PER_TICKET)

		self.notify(self.refund_id(), "processed", CHARGED_PER_TICKET)
		self.notify(self.refund_id(), "processed", CHARGED_PER_TICKET)

		self.assertEqual(len(self.refunds()), 1)
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)

	def test_a_failed_refund_is_not_counted_and_cancels_nothing(self):
		ticket = self.refundable_tickets()[0]
		self.initiate(CHARGED_PER_TICKET, tickets=[ticket])

		self.notify(self.refund_id(), "failed", CHARGED_PER_TICKET)

		self.assertEqual(self.refunds()[0].status, "Failed")
		self.assertEqual(self.booking.refunded_amount, 0)
		self.assertEqual(self.cancellation_requests(), [])
		self.assertEqual(frappe.db.get_value("Event Ticket", ticket, "docstatus"), 1)

	def test_a_webhook_processed_as_guest_still_updates_the_booking(self):
		# The webhook is an allow_guest endpoint, so its job runs as Guest.
		self.initiate(CHARGED_PER_TICKET, tickets=self.refundable_tickets()[:1])
		log = self.create_refund_log(self.refund_payload(self.refund_id(), "processed", CHARGED_PER_TICKET))

		with self.set_user("Guest"):
			self.handle_refund_log(log)

		self.assertEqual(self.refunds()[0].status, "Processed")
		self.assertEqual(self.booking.refund_status, "Partially Refunded")
		self.assertEqual([request.docstatus for request in self.cancellation_requests()], [1])

	def test_a_processed_refund_raises_and_submits_the_cancellation(self):
		ticket = self.refundable_tickets()[0]
		self.initiate(CHARGED_PER_TICKET, tickets=[ticket])

		self.notify(self.refund_id(), "processed", CHARGED_PER_TICKET)

		request = frappe.get_doc("Ticket Cancellation Request", self.refunds()[0].cancellation_request)
		self.assertEqual((request.status, request.docstatus), ("Accepted", 1))
		self.assertEqual(frappe.db.get_value("Event Ticket", ticket, "docstatus"), 2)

	def test_a_cancellation_that_cannot_go_through_leaves_the_refund_recorded(self):
		ticket = self.refundable_tickets()[0]
		self.initiate(CHARGED_PER_TICKET, tickets=[ticket])

		with patch("frappe.sendmail", side_effect=Exception("no outgoing email account")):
			self.refunds()[0].apply_gateway_status("processed", CHARGED_PER_TICKET)

		self.booking.reload()
		self.assertEqual(self.refunds()[0].status, "Processed")
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)
		request = frappe.get_doc("Ticket Cancellation Request", self.refunds()[0].cancellation_request)
		self.assertEqual((request.status, request.docstatus), ("In Review", 0))
		self.assertEqual(frappe.db.get_value("Event Ticket", ticket, "docstatus"), 1)

	def test_the_integration_request_is_linked_back_to_the_booking(self):
		self.initiate(CHARGED_PER_TICKET)

		log = self.notify(self.refund_id(), "processed", CHARGED_PER_TICKET)

		self.assertEqual(
			frappe.db.get_value("Integration Request", log, "reference_docname"), self.booking.name
		)

	def test_a_refund_for_an_unknown_payment_is_ignored(self):
		payload = self.refund_payload(self.refund_id(), "processed", CHARGED_PER_TICKET)
		payload["payload"]["refund"]["entity"]["payment_id"] = "pay_unknown"

		self.assertIsNone(handle_refund_notification("Integration Request", self.create_refund_log(payload)))
		self.assertEqual(self.refunds(), [])

	def test_a_payload_without_a_refund_is_refused(self):
		# Only refund events reach this handler, so one without a refund is a defect.
		log = self.create_refund_log({"event": "refund.processed", "payload": {}})

		self.assertRaises(ValidationError, handle_refund_notification, "Integration Request", log)


class TestSyncRefunds(BookingRefundTestCase):
	def setUp(self):
		super().setUp()
		self.make_payment()

	def test_a_refund_raised_outside_buzz_is_recorded(self):
		result = self.sync(self.gateway_refund("processed", CHARGED_PER_TICKET))

		self.assertEqual(result, {"refunds": 1, "created": 1})
		self.assertEqual([refund.status for refund in self.refunds()], ["Processed"])
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)
		self.assertEqual(self.booking.refund_status, "Partially Refunded")

	def test_a_payment_with_no_refunds_records_nothing(self):
		result = self.sync()

		self.assertEqual(result, {"refunds": 0, "created": 0})
		self.assertEqual(self.refunds(), [])
		self.assertEqual(self.booking.refund_status, "")

	def test_a_full_refund_raised_outside_buzz_cancels_every_remaining_ticket(self):
		self.sync(self.gateway_refund("processed", BOOKING_TOTAL))

		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual(len(self.refunds()[0].tickets), 2)
		self.assertEqual([request.docstatus for request in self.cancellation_requests()], [1])

	def test_a_partial_refund_raised_outside_buzz_cancels_nothing(self):
		self.sync(self.gateway_refund("processed", CHARGED_PER_TICKET))

		self.assertEqual(self.refunds()[0].tickets, [])
		self.assertEqual(self.cancellation_requests(), [])

	def test_a_refund_the_gateway_still_calls_pending_is_initiated(self):
		self.sync(self.gateway_refund("pending", BOOKING_TOTAL))

		self.assertEqual(self.refunds()[0].status, "Initiated")
		self.assertEqual(self.booking.refund_status, "Refund Initiated")
		self.assertEqual(self.booking.refunded_amount, 0)
		self.assertEqual(self.cancellation_requests(), [])

	def test_a_refund_buzz_already_holds_is_updated_not_duplicated(self):
		ticket = self.refundable_tickets()[0]
		self.initiate(CHARGED_PER_TICKET, tickets=[ticket])

		result = self.sync(self.gateway_refund("processed", CHARGED_PER_TICKET))

		self.assertEqual(result, {"refunds": 1, "created": 0})
		self.assertEqual([refund.status for refund in self.refunds()], ["Processed"])
		self.assertEqual([row.ticket for row in self.refunds()[0].tickets], [ticket])
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)

	def test_a_settled_refund_is_not_knocked_back_by_a_stale_pending(self):
		self.sync(self.gateway_refund("processed", BOOKING_TOTAL))

		self.sync(self.gateway_refund("pending", BOOKING_TOTAL))

		self.assertEqual(self.refunds()[0].status, "Processed")
		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual(self.booking.refunded_amount, BOOKING_TOTAL)
		self.assertEqual(len(self.cancellation_requests()), 1)

	def test_a_failed_refund_is_not_revived_by_a_later_sighting(self):
		self.sync(self.gateway_refund("failed", CHARGED_PER_TICKET))

		self.sync(self.gateway_refund("processed", CHARGED_PER_TICKET))

		self.assertEqual(self.refunds()[0].status, "Failed")
		self.assertEqual(self.booking.refunded_amount, 0)

	def test_a_refund_the_webhook_recorded_is_not_duplicated_by_a_sync(self):
		self.notify(self.refund_id(), "processed", CHARGED_PER_TICKET)

		result = self.sync(self.gateway_refund("processed", CHARGED_PER_TICKET))

		self.assertEqual(result, {"refunds": 1, "created": 0})
		self.assertEqual(len(self.refunds()), 1)
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)

	def test_syncing_twice_does_not_count_the_same_refund_twice(self):
		refund = self.gateway_refund("processed", CHARGED_PER_TICKET)

		self.sync(refund)
		self.sync(refund)

		self.assertEqual(len(self.refunds()), 1)
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)

	def test_a_checked_in_ticket_is_never_cancelled_by_a_synced_refund(self):
		used, unused = self.refundable_tickets()
		self.check_in(used)

		self.sync(self.gateway_refund("processed", BOOKING_TOTAL))

		self.assertEqual([row.ticket for row in self.refunds()[0].tickets], [unused])

	def test_two_refunds_in_one_batch_cancel_the_tickets_once_they_cover_the_total(self):
		# Neither half covers the booking alone; the second one pays back the last of it.
		self.sync(
			self.gateway_refund("processed", CHARGED_PER_TICKET, suffix="1"),
			self.gateway_refund("processed", CHARGED_PER_TICKET, suffix="2"),
		)

		first, second = self.refunds()
		self.assertEqual((first.tickets, len(second.tickets)), ([], 2))
		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual([request.docstatus for request in self.cancellation_requests()], [1])

	def test_sync_is_refused_when_the_gateway_is_not_razorpay(self):
		other_gateway = PaymentGatewayFactory.create().name
		frappe.db.set_value("Event Payment", self.payment.name, "payment_gateway", other_gateway)

		with self.assertRaises(frappe.ValidationError) as raised:
			self.booking.sync_refunds()

		self.assertIn("Razorpay", str(raised.exception))

	def test_sync_is_refused_without_a_received_payment(self):
		frappe.db.set_value("Event Payment", self.payment.name, "payment_received", 0)

		self.assertRaises(frappe.ValidationError, self.booking.sync_refunds)

	def gateway_refund(self, status: str, amount: float, suffix: str = "1") -> dict:
		return {"id": self.refund_id(suffix), "status": status, "amount": int(amount * 100)}

	def sync(self, *gateway_refunds: dict) -> dict:
		client = MagicMock()
		client.fetch_refunds.return_value = list(gateway_refunds)

		with patch(GATEWAY_CONTROLLER, return_value=client), patch("frappe.sendmail"):
			result = self.booking.sync_refunds()

		self.booking.reload()
		return result
