import frappe

from buzz.api.forms.schemas import CustomFormResponse, EventProposalFormResponse
from buzz.api.forms.services import (
	CustomFormService,
	create_event_proposal,
	get_dial_code_list,
	get_event_proposal_form,
)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_dial_codes() -> list:
	return get_dial_code_list()


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_custom_form_data(event_route: str, form_route: str) -> CustomFormResponse:
	return CustomFormService(event_route, form_route).form_data()


# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_custom_form(
	event_route: str, form_route: str, data: dict | str, custom_fields_data: dict | str | None = None
) -> None:
	CustomFormService(event_route, form_route).submit(data, custom_fields_data)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_event_proposal_form_data() -> EventProposalFormResponse:
	return get_event_proposal_form()


# nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
def submit_event_proposal(data: dict | str) -> None:
	create_event_proposal(data)
