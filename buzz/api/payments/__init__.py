import frappe

from buzz.payments import get_payment_gateways_for_event


@frappe.whitelist()
def get_event_payment_gateways(event: str) -> list[str]:
	return get_payment_gateways_for_event(event)
