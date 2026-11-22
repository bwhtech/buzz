# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from bwh_payments.base_class import CheckoutSession, PaymentGatewayBase, RefundResult, WebhookEvent
from bwh_payments.services import GatewayRefusedError, GatewayUnavailableError
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url
from frappe.utils.caching import redis_cache

from buzz.hosted_payments import hub

WEBHOOK_PATH = "/api/method/bwh_payments.bwh_payments.webhook.handle?gateway=Buzz"


class BuzzGatewaySettings(Document, PaymentGatewayBase):
	description = "Take payments through buzz.events, which pays them out to you later."
	idempotent_refunds = True

	def create_session(
		self,
		amount: float,
		currency: str,
		reference: str | None = None,
		customer: dict | None = None,
		return_url: str | None = None,
		description: str | None = None,
	) -> CheckoutSession:
		# The hub writes its own checkout description, naming the team.
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

	def refund_payment(
		self,
		session_id: str,
		amount: float,
		currency: str | None = None,
		idempotency_key: str | None = None,
		transaction_ref: str | None = None,
	) -> RefundResult:
		# The hub finds the payment from the order, so `transaction_ref` is not needed.
		try:
			return read_refund(
				hub.call_hub(
					"refund", "POST", order_id=session_id, amount=amount, idempotency_key=idempotency_key
				)
			)
		except Exception as error:
			frappe.clear_last_message()
			if is_hub_refusal(error):
				frappe.throw(str(error), GatewayRefusedError, title=_("buzz.events"))
			# The hub may have made it, so the refund stays Pending and a sync sends it again with its key.
			frappe.throw(_("buzz.events did not confirm the refund."), GatewayUnavailableError)

	def get_refund_status(self, session_id: str, refund_id: str) -> RefundResult:
		# POST: the hub may refresh the refund from its gateway.
		return RefundResult(
			**hub.call_hub("get_refund_status", "POST", order_id=session_id, refund_id=refund_id)
		)

	def handle_webhook(self, payload: bytes, headers: dict) -> WebhookEvent | None:
		# Anyone can post here, so the status is read back from the hub, never from the body.
		order_id = read_order_id(payload)
		if not order_id:
			return None
		return WebhookEvent(session_id=order_id, status="Pending", sync_status=True)

	def supported_currencies(self) -> tuple[str, ...]:
		return get_hub_currencies()


def read_refund(answer: dict) -> RefundResult:
	"""bwh_payments reads a missing status as Processed, so an answer without one is not a refund."""
	result = RefundResult.model_validate(answer)
	if not (result.refund_id and result.status):
		raise ValueError(answer)
	return result


def is_hub_refusal(error: Exception) -> bool:
	"""A named 4xx, which the hub answers before it refunds. A 417 is an error nobody named, and can come after."""
	status_code = getattr(error, "http_status_code", None)
	return isinstance(status_code, int) and 400 <= status_code < 500 and status_code not in (408, 417, 429)


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
