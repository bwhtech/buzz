# Copyright (c) 2026, BWH Studios and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

TICKET_PRICE = 500
ORDER_ID = "order_sync_1"


def make_payment_gateway(gateway: str) -> None:
	if not frappe.db.exists("Payment Gateway", gateway):
		frappe.get_doc({"doctype": "Payment Gateway", "gateway": gateway}).insert()


class PaymentSyncTestCase(IntegrationTestCase):
	def setUp(self):
		self.event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self.ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.event.name,
				"title": "Syncable",
				"price": TICKET_PRICE,
				"is_published": True,
			}
		).insert()

		# A booking left behind by a buyer who never came back from the gateway.
		self.booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event.name,
				"user": "Administrator",
				"payment_status": "Unpaid",
				"status": "Approval Pending",
				"attendees": [
					{"ticket_type": self.ticket_type.name, "first_name": "John", "email": "john@example.com"}
				],
			}
		).insert()

	def make_payment(self, gateway: str = "Razorpay", order_id: str | None = ORDER_ID):
		make_payment_gateway(gateway)
		return frappe.get_doc(
			{
				"doctype": "Event Payment",
				"user": "Administrator",
				"amount": self.booking.total_amount,
				"currency": self.booking.currency,
				"reference_doctype": "Event Booking",
				"reference_docname": self.booking.name,
				"payment_gateway": gateway,
				"payment_received": 0,
				"order_id": order_id,
			}
		).insert()

	def sync(self, *attempts: dict) -> dict:
		client = MagicMock()
		client.order.payments.return_value = {"items": list(attempts)}
		controller = MagicMock()
		controller.get_client.return_value = client

		with (
			patch(
				"buzz.ticketing.doctype.event_booking.payment_sync.get_controller", return_value=controller
			),
			patch("frappe.sendmail"),
		):
			result = self.booking.sync_payment_status()

		self.booking.reload()
		return result


class TestPaymentSync(PaymentSyncTestCase):
	def test_a_captured_payment_confirms_the_booking_and_issues_tickets(self):
		payment = self.make_payment()

		result = self.sync({"id": "pay_1", "status": "captured"})

		self.assertEqual(result["payment_status"], "Paid")
		self.assertEqual(self.booking.payment_status, "Paid")
		self.assertEqual(self.booking.status, "Confirmed")
		self.assertEqual(self.booking.docstatus, 1)
		self.assertEqual(frappe.db.count("Event Ticket", {"booking": self.booking.name}), 1)

		payment.reload()
		self.assertEqual(payment.payment_received, 1)
		self.assertEqual(payment.payment_id, "pay_1")

	def test_an_authorized_payment_confirms_the_booking_too(self):
		self.make_payment()

		self.sync({"id": "pay_1", "status": "authorized"})

		self.assertEqual(self.booking.payment_status, "Paid")

	def test_a_capture_wins_over_an_earlier_failed_attempt(self):
		self.make_payment()

		self.sync({"id": "pay_1", "status": "failed"}, {"id": "pay_2", "status": "captured"})

		self.assertEqual(self.booking.payment_status, "Paid")

	def test_only_failed_attempts_mark_the_booking_failed(self):
		self.make_payment()

		result = self.sync(
			{"id": "pay_1", "status": "failed", "error_description": "Card declined"},
		)

		self.assertEqual(result["payment_status"], "Failed")
		self.assertIn("Card declined", result["message"])
		self.assertEqual(self.booking.payment_status, "Failed")
		self.assertEqual(self.booking.docstatus, 0)
		self.assertEqual(frappe.db.count("Event Ticket", {"booking": self.booking.name}), 0)

	def test_an_order_nobody_paid_leaves_the_booking_alone(self):
		self.make_payment()

		result = self.sync()

		self.assertEqual(result["payment_status"], "Unpaid")
		self.assertEqual(self.booking.payment_status, "Unpaid")

	def test_a_paid_booking_is_left_alone(self):
		self.booking.db_set("payment_status", "Paid")
		self.booking.reload()

		self.assertEqual(self.booking.sync_payment_status()["payment_status"], "Paid")

	def test_syncing_is_refused_without_a_pending_payment(self):
		with self.assertRaises(frappe.ValidationError) as raised:
			self.booking.sync_payment_status()

		self.assertIn("No pending payment", str(raised.exception))

	def test_syncing_is_refused_when_the_gateway_is_not_razorpay(self):
		self.make_payment(gateway="PayPal")

		with self.assertRaises(frappe.ValidationError) as raised:
			self.booking.sync_payment_status()

		self.assertIn("Razorpay", str(raised.exception))

	def test_an_order_id_missing_from_the_payment_is_recovered_from_the_request_log(self):
		payment = self.make_payment(order_id=None)
		frappe.get_doc(
			{
				"doctype": "Integration Request",
				"integration_request_service": "Razorpay",
				"reference_doctype": "Event Booking",
				"reference_docname": self.booking.name,
				"data": frappe.as_json({"order_id": "order_from_log"}),
			}
		).insert()

		self.sync({"id": "pay_1", "status": "captured"})

		payment.reload()
		self.assertEqual(payment.order_id, "order_from_log")
		self.assertEqual(self.booking.payment_status, "Paid")

	def test_syncing_is_refused_when_no_order_was_ever_raised(self):
		self.make_payment(order_id=None)

		with self.assertRaises(frappe.ValidationError) as raised:
			self.booking.sync_payment_status()

		self.assertIn("order", str(raised.exception))
