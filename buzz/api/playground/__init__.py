import frappe
from frappe.rate_limiter import rate_limit

from buzz.api.playground import services
from buzz.api.playground.schemas import ChecklistGroup, InboxEmail, RedirectResponse


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
# Visitors at one event share an IP, so the limit only stops scripted floods.
@rate_limit(limit=30, seconds=3600)
def start() -> RedirectResponse:
	return services.start()


@frappe.whitelist(methods=["POST"])
# Same ceiling as start: a reset makes a whole new sandbox, and one event's visitors share an IP.
@rate_limit(limit=30, seconds=3600)
def reset() -> RedirectResponse:
	return services.reset()


@frappe.whitelist(methods=["POST"])
def switch_persona(persona: str, redirect_to: str | None = None) -> RedirectResponse:
	return services.switch_persona(persona, redirect_to)


@frappe.whitelist()
def get_checklist() -> list[ChecklistGroup]:
	return services.get_checklist()


@frappe.whitelist()
def get_inbox() -> list[InboxEmail]:
	return services.get_inbox()


@frappe.whitelist()
def download_attachment(file: str) -> None:
	services.download_attachment(file)
