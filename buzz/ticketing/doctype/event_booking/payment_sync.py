# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from buzz.payments import get_controller

RAZORPAY = "Razorpay"

# What Razorpay calls a payment that went through, and one that did not.
PAID_STATUSES = ("captured", "authorized")
FAILED_STATUS = "failed"


class BookingPaymentSync:
	"""Reconcile a booking still waiting on payment against what the gateway holds.

	Buzz confirms a booking off the browser redirect, so a buyer who paid and then
	closed the tab leaves the booking unpaid here and paid at Razorpay.
	"""

	def __init__(self, booking):
		self.booking = booking

	def run(self) -> dict:
		if self.booking.payment_status == "Paid":
			return self.result("Paid", _("This booking is already paid."))

		if self.booking.docstatus != 0:
			frappe.throw(_("Only a booking still waiting on payment can be synced"))

		payment = self.get_pending_payment()
		gateway_payment = self.get_decisive_payment(payment)

		if not gateway_payment:
			return self.result("Unpaid", _("Razorpay holds no payment attempt against this booking."))

		if gateway_payment.get("status") in PAID_STATUSES:
			return self.confirm(payment, gateway_payment)

		return self.mark_failed(gateway_payment)

	def get_pending_payment(self) -> frappe._dict:
		payment = frappe.get_all(
			"Event Payment",
			filters={
				"reference_doctype": self.booking.doctype,
				"reference_docname": self.booking.name,
				"payment_received": 0,
			},
			fields=["name", "payment_gateway", "order_id"],
			order_by="creation desc",
			limit=1,
		)

		if not payment:
			frappe.throw(_("No pending payment found for this booking"))

		if payment[0].payment_gateway != RAZORPAY:
			frappe.throw(_("Syncing is only supported for Razorpay at the moment"))

		payment[0].order_id = payment[0].order_id or self.recover_order_id(payment[0].name)
		return payment[0]

	def recover_order_id(self, payment: str) -> str:
		"""Bookings paid for before the order id was stored keep it on their request log."""
		# A payment attempt leaves more than one request log behind and only the
		# last of them carries the order, so the newest few are all considered.
		logged = frappe.get_all(
			"Integration Request",
			filters={"reference_doctype": self.booking.doctype, "reference_docname": self.booking.name},
			pluck="data",
			order_by="creation desc",
			limit=5,
		)

		order_ids = (frappe.parse_json(data).get("order_id") for data in logged)
		order_id = next((order_id for order_id in order_ids if order_id), None)
		if not order_id:
			frappe.throw(_("No Razorpay order was ever raised for this booking"))

		frappe.db.set_value("Event Payment", payment, "order_id", order_id)
		return order_id

	def get_decisive_payment(self, payment: frappe._dict) -> dict | None:
		"""The attempt on the order that settles the booking: one that went through,
		or failing that the last one that did not."""
		attempts = self.fetch_order_payments(payment.order_id)
		succeeded = [attempt for attempt in attempts if attempt.get("status") in PAID_STATUSES]
		failed = [attempt for attempt in attempts if attempt.get("status") == FAILED_STATUS]
		# Razorpay does not promise an order for the attempts, so the latest
		# failure is picked by when it was made rather than by where it sits.
		latest_failure = max(failed, key=lambda attempt: attempt.get("created_at") or 0, default=None)

		return next(iter(succeeded), None) or latest_failure

	def fetch_order_payments(self, order_id: str) -> list[dict]:
		client = get_controller(RAZORPAY).get_client()
		try:
			return client.order.payments(order_id).get("items", [])
		except Exception:
			frappe.log_error("Razorpay order payment fetch failed", frappe.get_traceback())
			frappe.throw(_("Razorpay could not be reached. Check the Error Log."))

	def confirm(self, payment: frappe._dict, gateway_payment: dict) -> dict:
		"""Record what the gateway took and put the booking through its usual confirmation."""
		frappe.db.set_value(
			"Event Payment",
			payment.name,
			{"payment_received": 1, "payment_id": gateway_payment.get("id")},
		)

		# Same two fields `on_payment_authorized` sets, so submitting issues the
		# tickets and sends the confirmation exactly as a live payment would.
		self.booking.payment_status = "Paid"
		self.booking.status = "Confirmed"
		self.booking.flags.ignore_permissions = True
		self.booking.submit()

		return self.result("Paid", _("Razorpay has this booking paid. Tickets have been issued."))

	def mark_failed(self, gateway_payment: dict) -> dict:
		self.booking.db_set("payment_status", "Failed", notify=True)

		return self.result(
			"Failed",
			_("Razorpay declined the last attempt: {0}").format(
				gateway_payment.get("error_description") or _("no reason given")
			),
		)

	def result(self, payment_status: str, message: str) -> dict:
		return {"payment_status": payment_status, "message": message}
