import frappe
from bwh_payments.api import get_gateway_options

from buzz.api.payments.currencies import enabled_currencies
from buzz.api.payments.schemas import CurrencyItem, PaymentGatewayLogo
from buzz.payments import get_payment_gateways_for_event


@frappe.whitelist()
def get_event_payment_gateways(event: str) -> list[str]:
	return get_payment_gateways_for_event(event)


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True)
def get_enabled_currencies() -> list[CurrencyItem]:
	return [CurrencyItem(**currency) for currency in enabled_currencies()]


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True)
def get_payment_gateway_logos() -> list[PaymentGatewayLogo]:
	return [
		PaymentGatewayLogo(name=option.name, logo=option.logo, logo_dark=option.logo_dark)
		for option in get_gateway_options()
		if option.logo
	]
