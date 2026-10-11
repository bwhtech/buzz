import frappe
from bwh_payments.api import record_external_payment, record_external_refund
from bwh_payments.migrate.frappe_payments import import_gateways


def execute():
	PaymentHistoryMigration().run()


class PaymentHistoryMigration:
	"""Give every payment and refund taken through frappe/payments a bwh_payments record.

	Event Payment and Event Booking Refund rows keep every field they had; they only gain a link.
	"""

	def run(self):
		import_gateways()
		for payment in frappe.get_all(
			"Event Payment",
			filters={"payment_request": ("is", "not set"), "payment_gateway": ("is", "set")},
			fields=["*"],
			order_by="creation asc",
		):
			self.import_row(self.import_payment, payment)

		for refund in frappe.get_all(
			"Event Booking Refund",
			filters={"gateway_refund": ("is", "not set"), "refund_id": ("is", "set")},
			fields=["name", "payment", "refund_id", "status", "amount"],
			order_by="creation asc",
		):
			self.import_row(self.import_refund, refund)

	def import_row(self, importer, row):
		# One unreadable row, such as a payment for a deleted booking, must not stop the site migrating.
		frappe.db.savepoint("move_payment_row")
		try:
			importer(row)
		except Exception:
			frappe.db.rollback(save_point="move_payment_row")
			frappe.log_error(title=f"Could not move payment record {row.name} to bwh_payments")

	def import_payment(self, payment):
		self.keep_gateway(payment.payment_gateway)
		payment_request = record_external_payment(
			payment.reference_doctype,
			payment.reference_docname,
			payment.amount,
			payment.currency,
			payment.payment_gateway,
			"Paid" if payment.payment_received else "Expired",
			payment.order_id or payment.payment_id or f"legacy-{payment.name}",
			transaction_ref=payment.payment_id,
		)
		frappe.db.set_value(
			"Event Payment", payment.name, "payment_request", payment_request.name, update_modified=False
		)

	def import_refund(self, refund):
		payment_request = frappe.db.get_value("Event Payment", refund.payment, "payment_request")
		if not payment_request:
			return

		gateway_refund = record_external_refund(
			payment_request, refund.refund_id, refund.status, refund.amount, reference=refund.name
		)
		frappe.db.set_value(
			"Event Booking Refund", refund.name, "gateway_refund", gateway_refund.name, update_modified=False
		)

	def keep_gateway(self, gateway: str):
		"""A gateway frappe/payments no longer lists is kept, disabled, so its payments still name it."""
		if not frappe.db.exists("Payment Gateway Profile", gateway):
			frappe.get_doc({"doctype": "Payment Gateway Profile", "name": gateway, "enabled": 0}).insert(
				ignore_permissions=True
			)
