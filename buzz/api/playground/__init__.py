import frappe
from frappe.rate_limiter import rate_limit

from buzz.api.playground import services
from buzz.api.playground.schemas import InboxEmail, RedirectResponse


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=3600)
def start() -> RedirectResponse:
	return services.start()


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=5, seconds=3600)
def reset() -> RedirectResponse:
	return services.reset()


@frappe.whitelist(methods=["POST"])
def switch_persona(persona: str) -> RedirectResponse:
	return services.switch_persona(persona)


@frappe.whitelist()
def get_inbox() -> list[InboxEmail]:
	return services.get_inbox()


@frappe.whitelist()
def download_attachment(file: str) -> None:
	services.download_attachment(file)
