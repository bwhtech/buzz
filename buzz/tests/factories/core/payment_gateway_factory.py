from typing import Any

import frappe
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory
from payments.payments.doctype.payment_gateway.payment_gateway import PaymentGateway


class PaymentGatewayFactory(BaseFactory[PaymentGateway]):
	doctype = "Payment Gateway"

	@property
	def default_attributes(self) -> dict[str, Any]:
		# Named after `gateway`, and rows outlive a run, so a hash beats Faker's per-process `unique`.
		return {"gateway": f"Gateway {frappe.generate_hash(length=8)}"}
