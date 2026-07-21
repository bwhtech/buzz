# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from buzz.payments import get_controller


class EventPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		currency: DF.Link | None
		name: DF.Int | None
		order_id: DF.Data | None
		payment_gateway: DF.Link | None
		payment_id: DF.Data | None
		payment_received: DF.Check
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		refund_id: DF.Data | None
		refund_status: DF.Literal["", "Refund Pending", "Partially Refunded", "Refunded"]
		refunded_amount: DF.Currency
		user: DF.Link
	# end: auto-generated types

	@frappe.whitelist()
	def refund(self, amount: float | None = None):
		frappe.only_for("System Manager")

		if not self.payment_received or not self.payment_id:
			frappe.throw(_("Only received payments can be refunded"))

		if self.refund_status == "Refunded":
			frappe.throw(_("This payment has already been fully refunded"))

		controller = get_controller(self.payment_gateway)
		if not hasattr(controller, "refund_payment"):
			frappe.throw(_("Refunds are not supported for {0}").format(self.payment_gateway))

		refund = controller.refund_payment(self.payment_id, amount)

		self.refund_id = refund.get("id")
		self.refunded_amount = flt(self.refunded_amount) + flt(refund.get("amount")) / 100
		self.set_refund_status(refund.get("status"))
		self.save()

		return self.refund_status

	@frappe.whitelist()
	def sync_refund_status(self):
		frappe.only_for("System Manager")

		if not self.refund_id:
			frappe.throw(_("No refund found on this payment"))

		controller = get_controller(self.payment_gateway)
		refund = controller.fetch_refund(self.refund_id)
		self.set_refund_status(refund.get("status"))
		self.save()

		return self.refund_status

	def set_refund_status(self, gateway_refund_status: str):
		if gateway_refund_status != "processed":
			self.refund_status = "Refund Pending"
		elif flt(self.refunded_amount) >= flt(self.amount):
			self.refund_status = "Refunded"
		else:
			self.refund_status = "Partially Refunded"
