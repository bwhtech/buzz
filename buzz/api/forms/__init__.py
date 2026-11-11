import sys

import frappe
from frappe.rate_limiter import rate_limit

from buzz.api.forms.builder import FormBuilderService
from buzz.api.forms.schemas import CustomFormResponse, EventProposalFormResponse, FormBuilderFields
from buzz.api.forms.services import (
	CustomFormService,
	create_event_proposal,
	get_dial_code_list,
	get_event_proposal_form,
)


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_dial_codes() -> list:
	return get_dial_code_list()


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_custom_form_data(event_route: str, form_route: str) -> CustomFormResponse:
	return form_service(event_route, form_route).form_data()


def custom_form_submit_limit() -> int:
	"""Attendees send feedback together from the venue's one IP, so feedback goes unlimited."""
	from buzz.events.doctype.buzz_form.form_types import EVENT_FEEDBACK_FORM_DOCTYPE

	request = frappe.form_dict
	if form_service(request.event_route, request.form_route).form_doctype == EVENT_FEEDBACK_FORM_DOCTYPE:
		return sys.maxsize
	return 20


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=custom_form_submit_limit, seconds=3600)
def submit_custom_form(
	event_route: str, form_route: str, data: dict | str, custom_fields_data: dict | str | None = None
) -> str | None:
	return form_service(event_route, form_route).submit(data, custom_fields_data)


def form_service(event_route: str, form_route: str):
	# Imported here: both modules read this package, so a module-level import cycles.
	from buzz.api.sponsorships.forms import SponsorFormService
	from buzz.events.doctype.buzz_form.form_types import SPONSORSHIP_FORM_DOCTYPE

	service = CustomFormService(event_route, form_route)
	if service.form_doctype == SPONSORSHIP_FORM_DOCTYPE:
		return SponsorFormService(event_route, form_route)
	return service


@frappe.whitelist(allow_guest=True)  # nosemgrep: guest-whitelisted-method
def get_event_proposal_form_data() -> EventProposalFormResponse:
	return get_event_proposal_form()


# nosemgrep: guest-whitelisted-method
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=10, seconds=3600)
def submit_event_proposal(data: dict | str) -> None:
	create_event_proposal(data)


@frappe.whitelist()
def get_form_builder_fields(form: str) -> FormBuilderFields:
	return FormBuilderService(form).fields()
