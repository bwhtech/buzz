from functools import lru_cache

import frappe
from frappe import _
from frappe.geo.country_info import get_all as get_all_countries
from frappe.model import DEFAULT_FIELDS, display_fieldtypes
from frappe.utils import get_datetime, now_datetime, today
from frappe.utils.data import cstr, sbool

LAYOUT_FIELDTYPES = set(display_fieldtypes)
LAYOUT_BREAK_FIELDTYPES = {"Column Break", "Section Break"}

EVENT_PROPOSAL_EXCLUDE_FIELDS = DEFAULT_FIELDS | {
	"naming_series",
	"amended_from",
	"host",
	"additional_notes",
	"status",
	"submitted_by",
}

STANDARD_EXCLUDE_FIELDS = DEFAULT_FIELDS | {
	"additional_fields",
	"event",
	"section_break_additional",
	"submitted_by",
	"status",
}


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_dial_codes() -> list:
	return _get_dial_codes()


@lru_cache(maxsize=1)
def _get_dial_codes() -> list:
	data = get_all_countries()
	codes = []
	seen = set()
	for country in sorted(data):
		info = data[country]
		isd = info.get("isd", "")
		code = (info.get("code") or "").upper()
		if isd and isd not in seen:
			codes.append({"country": country, "code": code, "dial_code": isd})
			seen.add(isd)
	return codes


def is_renderable_form_field(df, exclude_fields: set) -> bool:
	if df.fieldname in exclude_fields:
		return False
	if df.fieldtype in LAYOUT_FIELDTYPES:
		return False
	if df.hidden or df.read_only:
		return False
	return True


def get_form_fields(
	doctype: str,
	exclude_fields: set,
	with_layout_breaks: bool = False,
	event: str | None = None,
) -> list:
	meta = frappe.get_meta(doctype)
	fields = []
	for df in meta.fields:
		if not is_renderable_form_field(df, exclude_fields):
			if (
				with_layout_breaks
				and df.fieldtype in LAYOUT_BREAK_FIELDTYPES
				and df.fieldname not in exclude_fields
			):
				fields.append(
					{
						"fieldname": df.fieldname,
						"fieldtype": df.fieldtype,
						"label": df.label or "",
					}
				)
			continue
		default_value = df.default
		if default_value:
			if default_value == "Today":
				default_value = today()
			elif default_value == "Now":
				default_value = cstr(now_datetime())
			elif default_value.startswith("eval:") or default_value.startswith("%"):
				default_value = None

		field_data = {
			"fieldname": df.fieldname,
			"fieldtype": df.fieldtype,
			"label": df.label or df.fieldname,
			"options": df.options,
			"reqd": df.reqd,
			"default": default_value,
			"description": df.description,
		}
		if df.fieldtype == "Link" and df.options:
			field_data["link_options"] = get_link_field_options(df.options, event)
		if df.fieldtype == "Table" and df.options:
			child_meta = frappe.get_meta(df.options)
			child_fields = []
			for child_df in child_meta.fields:
				if child_df.fieldtype in LAYOUT_FIELDTYPES:
					continue
				if child_df.hidden:
					continue
				child_fields.append(
					{
						"fieldname": child_df.fieldname,
						"fieldtype": child_df.fieldtype,
						"label": child_df.label or child_df.fieldname,
						"options": child_df.options,
						"reqd": child_df.reqd,
					}
				)
			field_data["child_fields"] = child_fields
		fields.append(field_data)
	return fields


def get_link_field_options(doctype: str, event: str | None = None) -> list[dict]:
	meta = frappe.get_meta(doctype)
	title_field = meta.get_title_field()

	filters = {}
	if event and meta.has_field("event"):
		filters["event"] = event

	fields = ["name"] if title_field == "name" else ["name", title_field]
	rows = frappe.get_all(doctype, filters=filters, fields=fields, limit_page_length=0, order_by="name asc")
	return [{"value": row.name, "label": row.get(title_field) or row.name} for row in rows]


def validate_custom_form(event_route: str, form_route: str):
	event_name = frappe.get_cached_value("Buzz Event", {"route": event_route}, "name")
	if not event_name:
		frappe.throw(_("Event not found"), frappe.DoesNotExistError)
	event_doc = frappe.get_cached_doc("Buzz Event", event_name)

	if not event_doc.is_published:
		frappe.throw(_("Event not found"), frappe.DoesNotExistError)

	form_row = None
	for row in event_doc.custom_forms:
		if row.route == form_route and row.publish:
			form_row = row
			break

	if not form_row:
		frappe.throw(_("This form is not available for this event"), frappe.DoesNotExistError)

	return event_doc, form_row


def get_auto_set_fields(form_doctype: str):
	meta = frappe.get_meta(form_doctype)
	auto_set = {}
	for df in meta.fields:
		if df.fieldname == "event" and df.fieldtype == "Link":
			auto_set["event"] = "from_route"
		elif df.fieldname == "submitted_by" and df.fieldtype == "Link":
			auto_set["submitted_by"] = "session_user"
	return auto_set


def parse_excluded_fields(value: str | None) -> set | None:
	if not value:
		return None
	fieldnames = {fieldname.strip() for fieldname in value.split(",") if fieldname.strip()}
	return fieldnames or None


def get_renderable_fields(form_doctype: str, exclude_fields: set) -> dict:
	meta = frappe.get_meta(form_doctype)
	return {df.fieldname: df for df in meta.fields if is_renderable_form_field(df, exclude_fields)}


def validate_excluded_fields(form_doctype: str, excluded_fields: str | None) -> None:
	excluded = parse_excluded_fields(excluded_fields)
	if not excluded:
		return

	meta = frappe.get_meta(form_doctype)
	system_exclude = STANDARD_EXCLUDE_FIELDS | set(get_auto_set_fields(form_doctype).keys())
	# Blacklisting a system/auto-set field is a harmless no-op (it is never rendered anyway),
	# so they count as known names; only genuine typos are rejected.
	known_fieldnames = {df.fieldname for df in meta.fields} | system_exclude

	unknown = excluded - known_fieldnames
	if unknown:
		frappe.throw(
			_("These fields do not exist on the {0} form: {1}").format(
				form_doctype, ", ".join(sorted(unknown))
			)
		)

	renderable = get_renderable_fields(form_doctype, system_exclude)
	hidden_mandatory = {
		fieldname for fieldname in excluded if fieldname in renderable and renderable[fieldname].reqd
	}
	if hidden_mandatory:
		frappe.throw(
			_("These mandatory fields cannot be hidden on the {0} form: {1}").format(
				form_doctype, ", ".join(sorted(hidden_mandatory))
			)
		)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_custom_form_data(event_route: str, form_route: str) -> dict:
	event_doc, form_row = validate_custom_form(event_route, form_route)
	form_doctype = form_row.form_doctype

	if sbool(form_row.login_required) and frappe.session.user == "Guest":
		frappe.throw(_("Please log in to submit this form"), frappe.AuthenticationError)

	event_data = {
		"name": event_doc.name,
		"title": event_doc.title,
		"route": event_doc.route,
		"banner_image": event_doc.banner_image,
		"start_date": event_doc.start_date,
		"end_date": event_doc.end_date,
		"start_time": event_doc.start_time,
		"end_time": event_doc.end_time,
		"time_zone": event_doc.time_zone,
		"time_zone_label": event_doc.time_zone_label,
		"venue": event_doc.venue,
		"medium": event_doc.medium,
		"short_description": event_doc.short_description,
	}

	closed = False
	if form_row.auto_close_at and get_datetime(form_row.auto_close_at) < now_datetime():
		closed = True

	if closed:
		return {
			"form_fields": [],
			"custom_fields": [],
			"form_title": form_doctype,
			"event": event_data,
			"closed": True,
			"closed_title": form_row.closed_title or _("Submissions Closed"),
			"closed_message": form_row.closed_message or _("Submissions for this form have closed."),
			"success_title": "",
			"success_message": "",
		}

	auto_set = get_auto_set_fields(form_doctype)
	excluded_fields = parse_excluded_fields(form_row.excluded_fields) or set()
	exclude_fields = STANDARD_EXCLUDE_FIELDS | set(auto_set.keys()) | excluded_fields
	form_fields = get_form_fields(form_doctype, exclude_fields, with_layout_breaks=True, event=event_doc.name)

	form_doctype_meta = frappe.get_meta(form_doctype)
	custom_fields = []
	if form_doctype_meta.has_field("additional_fields"):
		custom_fields = frappe.get_all(
			"Buzz Custom Field",
			filters={
				"event": event_doc.name,
				"applied_to": "Custom Form",
				"custom_form_doctype": form_doctype,
				"enabled": 1,
			},
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

	return {
		"form_fields": form_fields,
		"custom_fields": custom_fields,
		"form_title": form_doctype_meta.name,
		"event": event_data,
		"closed": False,
		"closed_title": form_row.closed_title or _("Submissions Closed"),
		"closed_message": form_row.closed_message or _("Submissions for this form have closed."),
		"success_title": form_row.success_title or _("Thank you!"),
		"success_message": form_row.success_message or "",
	}


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def submit_custom_form(
	event_route: str, form_route: str, data: dict | str, custom_fields_data: dict | str | None = None
) -> None:
	event_doc, form_row = validate_custom_form(event_route, form_route)
	form_doctype = form_row.form_doctype

	if sbool(form_row.login_required) and frappe.session.user == "Guest":
		frappe.throw(_("Please login to submit this form"), frappe.AuthenticationError)

	if form_row.auto_close_at and get_datetime(form_row.auto_close_at) < now_datetime():
		frappe.throw(_("Submissions for this form have closed."))

	data = frappe.parse_json(data) or {}
	custom_fields_data = frappe.parse_json(custom_fields_data) or {}

	auto_set = get_auto_set_fields(form_doctype)
	excluded_fields = parse_excluded_fields(form_row.excluded_fields) or set()
	exclude_fields = STANDARD_EXCLUDE_FIELDS | set(auto_set.keys()) | excluded_fields

	doc_data = {"doctype": form_doctype}

	for field, source in auto_set.items():
		if source == "from_route":
			doc_data[field] = event_doc.name
		elif source == "session_user":
			doc_data[field] = frappe.session.user

	allowed_fieldnames = set(get_renderable_fields(form_doctype, exclude_fields))
	for fieldname, value in data.items():
		if fieldname in allowed_fieldnames:
			doc_data[fieldname] = value

	meta = frappe.get_meta(form_doctype)
	for df in meta.fields:
		if df.fieldtype == "Table" and df.fieldname in allowed_fieldnames:
			if df.fieldname in data and isinstance(data[df.fieldname], list):
				doc_data[df.fieldname] = data[df.fieldname]

	doc = frappe.get_doc(doc_data)

	if custom_fields_data and meta.has_field("additional_fields"):
		custom_field_definitions = frappe.get_all(
			"Buzz Custom Field",
			filters={
				"event": event_doc.name,
				"applied_to": "Custom Form",
				"custom_form_doctype": form_doctype,
				"enabled": 1,
			},
			fields=["fieldname", "label", "fieldtype"],
		)
		allowed_custom = {cf["fieldname"]: cf for cf in custom_field_definitions}

		for fieldname, value in custom_fields_data.items():
			if fieldname in allowed_custom and value not in (None, ""):
				cf = allowed_custom[fieldname]
				doc.append(
					"additional_fields",
					{
						"label": cf["label"],
						"fieldname": fieldname,
						"fieldtype": cf["fieldtype"],
						"value": cstr(value),
					},
				)

	doc.insert(ignore_permissions=True)


def validate_event_proposal_settings():
	settings = frappe.get_cached_doc("Buzz Settings")
	if not settings.accept_event_proposals:
		frappe.throw(_("Event Proposals are not being accepted"), frappe.DoesNotExistError)

	if not settings.allow_guest_event_proposals and frappe.session.user == "Guest":
		frappe.throw(_("Please log in to submit a proposal"), frappe.AuthenticationError)

	return settings


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_event_proposal_form_data() -> dict:
	settings = validate_event_proposal_settings()
	form_fields = get_form_fields("Event Proposal", EVENT_PROPOSAL_EXCLUDE_FIELDS, with_layout_breaks=True)

	return {
		"form_fields": form_fields,
		"form_title": _("Event Proposal"),
		"banner_title": settings.event_proposal_banner_title or _("Propose an Event"),
		"success_title": settings.event_proposal_success_title or _("Thank you!"),
		"success_message": settings.event_proposal_success_message or "",
	}


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def submit_event_proposal(data: dict | str) -> None:
	validate_event_proposal_settings()

	data = frappe.parse_json(data) or {}

	doc_data = {"doctype": "Event Proposal"}

	if frappe.session.user != "Guest":
		doc_data["submitted_by"] = frappe.session.user

	allowed_fieldnames = {
		f["fieldname"] for f in get_form_fields("Event Proposal", EVENT_PROPOSAL_EXCLUDE_FIELDS)
	}
	for fieldname, value in data.items():
		if fieldname in allowed_fieldnames:
			doc_data[fieldname] = value

	meta = frappe.get_meta("Event Proposal")
	for df in meta.fields:
		if df.fieldtype == "Table" and df.fieldname not in EVENT_PROPOSAL_EXCLUDE_FIELDS:
			if df.fieldname in data and isinstance(data[df.fieldname], list):
				doc_data[df.fieldname] = data[df.fieldname]

	frappe.get_doc(doc_data).insert(ignore_permissions=True)
