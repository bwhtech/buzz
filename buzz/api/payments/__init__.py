import frappe
from bwh_payments.api import get_gateway_options
from frappe.utils.caching import redis_cache

from buzz.api.payments.currencies import enabled_currencies
from buzz.api.payments.schemas import CurrencyItem, PaymentGatewayLogo
from buzz.payments import get_gateways_needing_phone, get_payment_gateways_for_event


@redis_cache(ttl=3600)
def _cached_gateway_logos() -> list[dict]:
	return [
		{"name": option.name, "logo": option.logo, "logo_dark": option.logo_dark}
		for option in get_gateway_options()
		if option.logo
	]


@frappe.whitelist()
def get_event_payment_gateways(event: str) -> list[str]:
	return get_payment_gateways_for_event(event)


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True)
def get_enabled_currencies() -> list[CurrencyItem]:
	return [CurrencyItem(**currency) for currency in enabled_currencies()]


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True)
def get_payment_gateways_needing_phone() -> list[str]:
	return get_gateways_needing_phone()


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True)
def get_payment_gateway_logos() -> list[PaymentGatewayLogo]:
	return [PaymentGatewayLogo(**row) for row in _cached_gateway_logos()]
