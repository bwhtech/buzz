# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from bwh_payments.base_class import CheckoutSession, PaymentGatewayBase, RefundResult, WebhookEvent
from frappe.model.document import Document
from frappe.utils import get_url
from frappe.utils.caching import redis_cache

from buzz.hosted_payments import hub

WEBHOOK_PATH = "/api/method/bwh_payments.bwh_payments.webhook.handle?gateway=Buzz"


class BuzzGatewaySettings(Document, PaymentGatewayBase):
	description = "Take payments through buzz.events, which pays them out to you later."

	def create_session(
		self,
		amount: float,
		currency: str,
		reference: str | None = None,
		customer: dict | None = None,
		return_url: str | None = None,
	) -> CheckoutSession:
		return_url = return_url or get_url()
		order = hub.call_hub(
			"create_order",
			"POST",
			amount=amount,
			currency=currency,
			reference=reference,
			customer=customer or {},
			return_url=return_url,
			webhook_url=get_url(WEBHOOK_PATH),
		)
		return CheckoutSession(
			session_id=order["order_id"],
			redirect_url=order["checkout_url"],
			success_url=return_url,
			cancel_url=return_url,
			failure_url=return_url,
		)

	def get_payment_status(self, session_id: str) -> str:
		return hub.call_hub("get_status", order_id=session_id)

	def refund_payment(self, session_id: str, amount: float, currency: str | None = None) -> RefundResult:
		# The hub always sends a status: bwh_payments reads a missing one as Processed.
		return RefundResult(**hub.call_hub("refund", "POST", order_id=session_id, amount=amount))

	def get_refund_status(self, session_id: str, refund_id: str) -> RefundResult:
		return RefundResult(**hub.call_hub("get_refund_status", order_id=session_id, refund_id=refund_id))

	def handle_webhook(self, payload: bytes, headers: dict) -> WebhookEvent | None:
		# Anyone can post here, so the status is read back from the hub, never from the body.
		order_id = read_order_id(payload)
		if not order_id:
			return None
		return WebhookEvent(session_id=order_id, status="Pending", sync_status=True)

	def supported_currencies(self) -> tuple[str, ...]:
		return get_hub_currencies()


def read_order_id(payload: bytes) -> str | None:
	try:
		body = frappe.parse_json(payload.decode())
	except ValueError:
		return None
	order_id = body.get("order_id") if isinstance(body, dict) else None
	return order_id if isinstance(order_id, str) else None


@redis_cache(ttl=60 * 60)
def get_hub_currencies() -> tuple[str, ...]:
	return tuple(hub.call_hub("get_currencies"))
