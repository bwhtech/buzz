import frappe
from frappe.model import DEFAULT_FIELDS, display_fieldtypes
from frappe.utils import cstr, now_datetime, today

from buzz.api.forms.exceptions import MandatoryFieldsHidden, UnknownExcludedFields

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


def get_form_fields(
	doctype: str,
	exclude_fields: set,
	with_layout_breaks: bool = False,
	event: str | None = None,
) -> list[dict]:
	fields = []
	for df in frappe.get_meta(doctype).fields:
		if is_renderable_form_field(df, exclude_fields):
			fields.append(build_field(df, event))
		elif with_layout_breaks and is_layout_break(df, exclude_fields):
			fields.append({"fieldname": df.fieldname, "fieldtype": df.fieldtype, "label": df.label or ""})
	return fields


def build_field(df, event: str | None) -> dict:
	field = {
		"fieldname": df.fieldname,
		"fieldtype": df.fieldtype,
		"label": df.label or df.fieldname,
		"options": df.options,
		"reqd": df.reqd,
		"default": resolve_default(df.default),
		"description": df.description,
	}
	if df.options and df.fieldtype == "Link":
		field["link_options"] = get_link_field_options(df.options, event)
	elif df.options and df.fieldtype == "Table":
		field["child_fields"] = get_child_fields(df.options)
	return field


def resolve_default(default_value: str | None) -> str | None:
	if not default_value:
		return default_value
	if default_value == "Today":
		return today()
	if default_value == "Now":
		return cstr(now_datetime())
	if default_value.startswith(("eval:", "%")):
		return None
	return default_value


def get_child_fields(child_doctype: str) -> list[dict]:
	return [
		{
			"fieldname": df.fieldname,
			"fieldtype": df.fieldtype,
			"label": df.label or df.fieldname,
			"options": df.options,
			"reqd": df.reqd,
		}
		for df in frappe.get_meta(child_doctype).fields
		if df.fieldtype not in LAYOUT_FIELDTYPES and not df.hidden
	]


def get_link_field_options(doctype: str, event: str | None = None) -> list[dict]:
	meta = frappe.get_meta(doctype)
	title_field = meta.get_title_field()

	filters = {}
	if event and meta.has_field("event"):
		filters["event"] = event

	fields = ["name"] if title_field == "name" else ["name", title_field]
	rows = frappe.get_all(doctype, filters=filters, fields=fields, limit_page_length=0, order_by="name asc")
	return [{"value": row.name, "label": row.get(title_field) or row.name} for row in rows]


def get_auto_set_fields(form_doctype: str) -> dict[str, str]:
	sources = {"event": "from_route", "submitted_by": "session_user"}
	return {
		df.fieldname: sources[df.fieldname]
		for df in frappe.get_meta(form_doctype).fields
		if df.fieldname in sources and df.fieldtype == "Link"
	}


def parse_excluded_fields(value: str | None) -> set | None:
	if not value:
		return None
	fieldnames = {fieldname.strip() for fieldname in value.split(",") if fieldname.strip()}
	return fieldnames or None


def get_renderable_fields(form_doctype: str, exclude_fields: set) -> dict:
	meta = frappe.get_meta(form_doctype)
	return {df.fieldname: df for df in meta.fields if is_renderable_form_field(df, exclude_fields)}


def get_exclude_fields(form_doctype: str, excluded_fields: str | None) -> set:
	auto_set = set(get_auto_set_fields(form_doctype))
	return STANDARD_EXCLUDE_FIELDS | auto_set | (parse_excluded_fields(excluded_fields) or set())


def validate_excluded_fields(form_doctype: str, excluded_fields: str | None) -> None:
	excluded = parse_excluded_fields(excluded_fields)
	if not excluded:
		return

	meta = frappe.get_meta(form_doctype)
	system_exclude = STANDARD_EXCLUDE_FIELDS | set(get_auto_set_fields(form_doctype))
	# Blacklisting a system/auto-set field is a harmless no-op (it is never rendered anyway),
	# so they count as known names; only genuine typos are rejected.
	known_fieldnames = {df.fieldname for df in meta.fields} | system_exclude

	unknown = excluded - known_fieldnames
	if unknown:
		UnknownExcludedFields.throw(form_doctype=form_doctype, fieldnames=", ".join(sorted(unknown)))

	renderable = get_renderable_fields(form_doctype, system_exclude)
	hidden_mandatory = {
		fieldname for fieldname in excluded if fieldname in renderable and renderable[fieldname].reqd
	}
	if hidden_mandatory:
		MandatoryFieldsHidden.throw(form_doctype=form_doctype, fieldnames=", ".join(sorted(hidden_mandatory)))


def is_renderable_form_field(df, exclude_fields: set) -> bool:
	if df.fieldname in exclude_fields:
		return False
	if df.fieldtype in LAYOUT_FIELDTYPES:
		return False
	return not (df.hidden or df.read_only)


def is_layout_break(df, exclude_fields: set) -> bool:
	return df.fieldtype in LAYOUT_BREAK_FIELDTYPES and df.fieldname not in exclude_fields
