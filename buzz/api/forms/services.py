from functools import lru_cache
from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.geo.country_info import get_all as get_all_countries
from frappe.utils import cstr, get_datetime, now_datetime
from frappe.utils.data import sbool

from buzz.api.forms.exceptions import (
	EventNotFound,
	FormNotAvailable,
	LoginRequired,
	ProposalsNotAccepted,
	SubmissionsClosed,
)
from buzz.api.forms.fields import (
	EVENT_PROPOSAL_EXCLUDE_FIELDS,
	get_auto_set_fields,
	get_exclude_fields,
	get_form_fields,
	get_renderable_fields,
)
from buzz.api.forms.schemas import (
	CustomFieldDefinition,
	CustomFormResponse,
	EventProposalFormResponse,
	FormEventSummary,
)

if TYPE_CHECKING:
	from frappe.model.document import Document

	from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent
	from buzz.events.doctype.buzz_event_form.buzz_event_form import BuzzEventForm


@lru_cache(maxsize=1)
def get_dial_code_list() -> list[dict]:
	countries = get_all_countries()
	codes = []
	seen = set()
	for country in sorted(countries):
		isd = countries[country].get("isd", "")
		if isd and isd not in seen:
			code = (countries[country].get("code") or "").upper()
			codes.append({"country": country, "code": code, "dial_code": isd})
			seen.add(isd)
	return codes


class CustomFormService:
	"""Resolve one published custom form on a published event, then read or submit it."""

	def __init__(self, event_route: str, form_route: str):
		self.event_route = event_route
		self.form_route = form_route

	@property
	def event(self) -> "BuzzEvent":
		event_name = frappe.get_cached_value("Buzz Event", {"route": self.event_route}, "name")
		if not event_name:
			EventNotFound.throw()

		event = frappe.get_cached_doc("Buzz Event", event_name)
		if not event.is_published:
			EventNotFound.throw()
		return event

	@property
	def form_row(self) -> "BuzzEventForm":
		for row in self.event.custom_forms:
			if row.route == self.form_route and row.publish:
				return row
		FormNotAvailable.throw()

	@property
	def form_doctype(self) -> str:
		return self.form_row.form_doctype

	@property
	def is_closed(self) -> bool:
		auto_close_at = self.form_row.auto_close_at
		return bool(auto_close_at) and get_datetime(auto_close_at) < now_datetime()

	def check_login(self) -> None:
		if sbool(self.form_row.login_required) and frappe.session.user == "Guest":
			LoginRequired.throw()

	def form_data(self) -> CustomFormResponse:
		self.check_login()
		if self.is_closed:
			return self.closed_response()

		form_row = self.form_row
		return CustomFormResponse(
			form_fields=self.renderable_fields(),
			custom_fields=self.custom_field_definitions(),
			form_title=self.form_doctype,
			event=self.event_summary(),
			closed=False,
			closed_title=form_row.closed_title or _("Submissions Closed"),
			closed_message=form_row.closed_message or _("Submissions for this form have closed."),
			success_title=form_row.success_title or _("Thank you!"),
			success_message=form_row.success_message or "",
		)

	def closed_response(self) -> CustomFormResponse:
		form_row = self.form_row
		return CustomFormResponse(
			form_fields=[],
			custom_fields=[],
			form_title=self.form_doctype,
			event=self.event_summary(),
			closed=True,
			closed_title=form_row.closed_title or _("Submissions Closed"),
			closed_message=form_row.closed_message or _("Submissions for this form have closed."),
			success_title="",
			success_message="",
		)

	def event_summary(self) -> FormEventSummary:
		event = self.event
		return FormEventSummary(
			name=str(event.name),
			title=event.title,
			route=event.route,
			banner_image=event.banner_image,
			start_date=event.start_date,
			end_date=event.end_date,
			start_time=event.start_time,
			end_time=event.end_time,
			time_zone=event.time_zone,
			time_zone_label=event.time_zone_label,
			venue=event.venue,
			medium=event.medium,
			short_description=event.short_description,
		)

	@property
	def exclude_fields(self) -> set:
		return get_exclude_fields(self.form_doctype, self.form_row.excluded_fields)

	def renderable_fields(self) -> list[dict]:
		return get_form_fields(
			self.form_doctype, self.exclude_fields, with_layout_breaks=True, event=self.event.name
		)

	def custom_field_definitions(self) -> list[CustomFieldDefinition]:
		if not frappe.get_meta(self.form_doctype).has_field("additional_fields"):
			return []

		rows = frappe.get_all(
			"Buzz Custom Field",
			filters=self.custom_field_filters,
			fields=[
				"label",
				"fieldname",
				"fieldtype",
				"options",
				"mandatory",
				"placeholder",
				"default_value",
				"order",
			],
			order_by="order asc",
		)
		return [CustomFieldDefinition(**row) for row in rows]

	@property
	def custom_field_filters(self) -> dict:
		return {
			"event": self.event.name,
			"applied_to": "Custom Form",
			"custom_form_doctype": self.form_doctype,
			"enabled": 1,
		}

	def submit(self, data: dict | str, custom_fields_data: dict | str | None = None) -> None:
		self.check_login()
		if self.is_closed:
			SubmissionsClosed.throw()

		doc = frappe.get_doc(self.build_doc_data(frappe.parse_json(data) or {}))
		self.append_custom_fields(doc, frappe.parse_json(custom_fields_data) or {})
		doc.insert(ignore_permissions=True)

	def build_doc_data(self, data: dict) -> dict:
		form_doctype = self.form_doctype
		doc_data = {"doctype": form_doctype}

		for fieldname, source in get_auto_set_fields(form_doctype).items():
			doc_data[fieldname] = self.event.name if source == "from_route" else frappe.session.user

		allowed_fieldnames = get_renderable_fields(form_doctype, self.exclude_fields)
		doc_data.update(
			{fieldname: value for fieldname, value in data.items() if fieldname in allowed_fieldnames}
		)
		return doc_data

	def append_custom_fields(self, doc: "Document", custom_fields_data: dict) -> None:
		if not custom_fields_data or not doc.meta.has_field("additional_fields"):
			return

		definitions = frappe.get_all(
			"Buzz Custom Field", filters=self.custom_field_filters, fields=["fieldname", "label", "fieldtype"]
		)
		allowed = {definition.fieldname: definition for definition in definitions}

		for fieldname, value in custom_fields_data.items():
			if fieldname in allowed and value not in (None, ""):
				definition = allowed[fieldname]
				doc.append(
					"additional_fields",
					{
						"label": definition.label,
						"fieldname": fieldname,
						"fieldtype": definition.fieldtype,
						"value": cstr(value),
					},
				)


def get_event_proposal_settings():
	settings = frappe.get_cached_doc("Buzz Settings")
	if not settings.accept_event_proposals:
		ProposalsNotAccepted.throw()

	if not settings.allow_guest_event_proposals and frappe.session.user == "Guest":
		LoginRequired.throw()

	return settings


def get_event_proposal_form() -> EventProposalFormResponse:
	settings = get_event_proposal_settings()
	return EventProposalFormResponse(
		form_fields=get_form_fields("Event Proposal", EVENT_PROPOSAL_EXCLUDE_FIELDS, with_layout_breaks=True),
		form_title=_("Event Proposal"),
		banner_title=settings.event_proposal_banner_title or _("Propose an Event"),
		success_title=settings.event_proposal_success_title or _("Thank you!"),
		success_message=settings.event_proposal_success_message or "",
	)


def create_event_proposal(data: dict | str) -> None:
	get_event_proposal_settings()
	data = frappe.parse_json(data) or {}

	doc_data = {"doctype": "Event Proposal"}
	if frappe.session.user != "Guest":
		doc_data["submitted_by"] = frappe.session.user

	allowed_fieldnames = {
		field["fieldname"] for field in get_form_fields("Event Proposal", EVENT_PROPOSAL_EXCLUDE_FIELDS)
	}
	doc_data.update(
		{fieldname: value for fieldname, value in data.items() if fieldname in allowed_fieldnames}
	)
	frappe.get_doc(doc_data).insert(ignore_permissions=True)
