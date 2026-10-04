import frappe

from buzz.api.payments.currencies import enabled_currencies
from buzz.api.payments.schemas import CurrencyItem
from buzz.payments import get_payment_gateways_for_event


@frappe.whitelist()
def get_event_payment_gateways(event: str) -> list[str]:
	return get_payment_gateways_for_event(event)


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True)
def get_enabled_currencies() -> list[CurrencyItem]:
	return [CurrencyItem(**currency) for currency in enabled_currencies()]
