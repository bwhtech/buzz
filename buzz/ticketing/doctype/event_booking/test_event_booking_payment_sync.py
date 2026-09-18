# Copyright (c) 2026, BWH Studios and Contributors
# See license.txt

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now

from buzz.payments import sync_gateway_payment
from buzz.tasks import sync_pending_online_payments

ORDER_ID = "order_sync_1"
TICKET_PRICE = 500


def make_payment_gateway(gateway: str) -> None:
	if not frappe.db.exists("Payment Gateway", gateway):
		frappe.get_doc({"doctype": "Payment Gateway", "gateway": gateway}).insert()


def razorpay_payment(payment_id: str = "pay_sync_1", status: str = "captured") -> dict:
	return {"id": payment_id, "status": status, "order_id": ORDER_ID}


class PaymentSyncTestCase(IntegrationTestCase):
	"""A booking left in draft because the browser never reported the payment."""

	def setUp(self):
		# Stubbed for the whole case, so no test can build a client or reach Razorpay.
		self.controller = self.patch_controller()

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

		self.booking = self.make_booking("John", "john@example.com")

		make_payment_gateway("Razorpay")
		self.payment = frappe.get_doc(
			{
				"doctype": "Event Payment",
				"user": "Administrator",
				"amount": self.booking.total_amount,
				"currency": self.booking.currency,
				"reference_doctype": "Event Booking",
				"reference_docname": self.booking.name,
				"payment_gateway": "Razorpay",
			}
		).insert()

	def patch_controller(self) -> MagicMock:
		patcher = patch("buzz.payments.get_controller")
		self.addCleanup(patcher.stop)
		controller = patcher.start().return_value
		controller.get_client().order.payments.return_value = {"items": []}
		return controller

	def set_order_payments(self, *payments: dict) -> None:
		"""What Razorpay answers when asked for the order's payments."""
		self.controller.get_client().order.payments.return_value = {"items": list(payments)}

	def order_payments_call(self) -> MagicMock:
		return self.controller.get_client().order.payments

	def make_booking(self, first_name: str, email: str) -> frappe.Document:
		return frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": self.ticket_type.name, "first_name": first_name, "email": email}
				],
			}
		).insert()

	def make_checkout_request(self, order_id: str = ORDER_ID) -> frappe.Document:
		"""The Integration Request the gateway logs when it hands out a checkout link."""
		return frappe.get_doc(
			{
				"doctype": "Integration Request",
				"integration_request_service": "Razorpay",
				"reference_doctype": "Event Booking",
				"reference_docname": self.booking.name,
				"status": "Queued",
				"data": json.dumps(
					{
						"order_id": order_id,
						"payment": self.payment.name,
						"payment_gateway": "Razorpay",
						"reference_doctype": "Event Booking",
						"reference_docname": self.booking.name,
					}
				),
			}
		).insert()

	def backdate(self, booking: str, minutes: int) -> None:
		"""Backdate a booking, since the sweep leaves a checkout still in flight alone."""
		frappe.db.set_value(
			"Event Booking", booking, "creation", add_to_date(now(), minutes=-minutes), update_modified=False
		)

	def sync(self) -> str:
		with patch("frappe.sendmail"):
			return sync_gateway_payment("Event Booking", self.booking.name)


class TestSyncGatewayPayment(PaymentSyncTestCase):
	def test_captured_payment_confirms_the_booking_and_issues_tickets(self):
		self.make_checkout_request()
		self.set_order_payments(razorpay_payment())

		status = self.sync()

		self.booking.reload()
		self.payment.reload()
		self.assertEqual(status, "Completed")
		self.assertEqual(self.booking.docstatus, 1)
		self.assertEqual(self.booking.payment_status, "Paid")
		self.assertEqual(self.booking.status, "Confirmed")
		self.assertEqual(self.payment.payment_received, 1)
		self.assertEqual(self.payment.payment_id, "pay_sync_1")
		self.assertEqual(self.payment.order_id, ORDER_ID)
		self.assertEqual(
			frappe.db.count("Event Ticket", {"booking": self.booking.name}), len(self.booking.attendees)
		)

	def test_authorized_payment_confirms_the_booking(self):
		self.make_checkout_request()
		self.set_order_payments(razorpay_payment(status="authorized"))

		self.assertEqual(self.sync(), "Authorized")

		self.booking.reload()
		self.assertEqual(self.booking.docstatus, 1)
		self.assertEqual(self.booking.payment_status, "Paid")

	def test_an_order_nobody_paid_leaves_the_booking_alone(self):
		self.make_checkout_request()

		self.assertEqual(self.sync(), "")

		self.booking.reload()
		self.payment.reload()
		self.assertEqual(self.booking.docstatus, 0)
		self.assertEqual(self.booking.payment_status, "Unpaid")
		self.assertEqual(self.payment.payment_received, 0)

	def test_a_failed_payment_leaves_the_booking_alone(self):
		self.make_checkout_request()
		self.set_order_payments(razorpay_payment(status="failed"))

		self.assertEqual(self.sync(), "")
		self.assertEqual(frappe.db.get_value("Event Booking", self.booking.name, "docstatus"), 0)

	def test_a_payment_already_received_is_never_asked_about_again(self):
		# The sweep runs over and over, so a settled payment must cost no API call.
		self.make_checkout_request()
		self.payment.db_set("payment_received", 1)
		self.set_order_payments(razorpay_payment())

		self.assertEqual(self.sync(), "")
		self.order_payments_call().assert_not_called()

	def test_a_booking_that_never_reached_the_gateway_is_not_an_error(self):
		self.set_order_payments(razorpay_payment())

		self.assertEqual(self.sync(), "")
		self.order_payments_call().assert_not_called()

	def test_a_gateway_that_cannot_be_asked_is_not_an_error(self):
		# The sweep walks every unpaid booking, so another gateway must not raise at it.
		make_payment_gateway("Paymob")
		self.payment.db_set("payment_gateway", "Paymob")
		self.make_checkout_request()
		self.set_order_payments(razorpay_payment())

		self.assertEqual(self.sync(), "")
		self.order_payments_call().assert_not_called()

	def test_the_order_created_log_is_not_mistaken_for_the_checkout_log(self):
		# Every checkout logs two requests, and only one of them carries the order id.
		frappe.get_doc(
			{
				"doctype": "Integration Request",
				"integration_request_service": "Razorpay",
				"reference_doctype": "Event Booking",
				"reference_docname": self.booking.name,
				"status": "Queued",
				"data": json.dumps({"payment": self.payment.name, "amount": 50000}),
			}
		).insert()
		self.make_checkout_request()
		self.set_order_payments(razorpay_payment())

		self.assertEqual(self.sync(), "Completed")
		self.order_payments_call().assert_called_once_with(ORDER_ID)


class TestBookingSyncPayment(PaymentSyncTestCase):
	def test_a_draft_booking_is_confirmed(self):
		self.make_checkout_request()
		self.set_order_payments(razorpay_payment())

		with patch("frappe.sendmail"):
			self.assertEqual(self.booking.sync_payment(), "Completed")

		self.assertEqual(frappe.db.get_value("Event Booking", self.booking.name, "docstatus"), 1)

	def test_a_confirmed_booking_is_never_asked_about_again(self):
		self.make_checkout_request()
		self.booking.payment_status = "Paid"
		self.booking.flags.ignore_permissions = True
		with patch("frappe.sendmail"):
			self.booking.submit()
		self.set_order_payments(razorpay_payment())

		self.assertEqual(self.booking.sync_payment(), "")
		self.order_payments_call().assert_not_called()

	def test_a_plain_user_may_not_sync(self):
		attendee = frappe.get_doc(
			{
				"doctype": "User",
				"email": "attendee-sync@example.com",
				"first_name": "Attendee",
				"roles": [{"role": "Buzz User"}],
			}
		).insert()
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(attendee.name)

		self.assertRaises(frappe.PermissionError, self.booking.sync_payment)


class TestPendingPaymentSweep(PaymentSyncTestCase):
	def sweep(self) -> None:
		with patch("frappe.sendmail"):
			sync_pending_online_payments()

	def test_a_stuck_booking_is_confirmed(self):
		self.make_checkout_request()
		self.backdate(self.booking.name, minutes=30)
		self.set_order_payments(razorpay_payment())

		self.sweep()

		self.booking.reload()
		self.assertEqual(self.booking.docstatus, 1)
		self.assertEqual(self.booking.payment_status, "Paid")

	def test_a_checkout_still_in_flight_is_left_alone(self):
		self.make_checkout_request()
		self.backdate(self.booking.name, minutes=2)
		self.set_order_payments(razorpay_payment())

		self.sweep()

		self.order_payments_call().assert_not_called()
		self.assertEqual(frappe.db.get_value("Event Booking", self.booking.name, "docstatus"), 0)

	def test_a_booking_abandoned_days_ago_is_left_alone(self):
		self.make_checkout_request()
		self.backdate(self.booking.name, minutes=10 * 24 * 60)
		self.set_order_payments(razorpay_payment())

		self.sweep()

		self.order_payments_call().assert_not_called()

	def test_one_broken_booking_does_not_stop_the_rest(self):
		self.backdate(self.booking.name, minutes=30)
		other = self.make_booking("Jenny", "jenny@example.com")
		self.backdate(other.name, minutes=30)

		with patch(
			"buzz.tasks.sync_gateway_payment", side_effect=[Exception("Razorpay is down"), "Completed"]
		) as sync:
			self.sweep()

		self.assertEqual(
			sorted(call.args[1] for call in sync.call_args_list), sorted([other.name, self.booking.name])
		)
