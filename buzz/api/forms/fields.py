import frappe
from frappe.model import DEFAULT_FIELDS, display_fieldtypes
from frappe.utils import cstr, now_datetime, today

LAYOUT_FIELDTYPES = set(display_fieldtypes)
LAYOUT_BREAK_FIELDTYPES = {"Column Break", "Section Break"}

# Masters a public form asks for; `get_list` refuses them to anyone without a permission, and no
# row on these is private. They are short, so they are offered whole.
PUBLIC_LINK_DOCTYPES = frozenset({"Country", "Event Host", "Event Category", "Sponsorship Tier"})
# A picker is a shortlist, not a listing.
LINK_OPTION_LIMIT = 100

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
	can_read = frappe.has_permission(doctype, "read")
	if not can_read and not is_open_reference(doctype, meta):
		return []
	title_field = meta.get_title_field()

	filters = {}
	if event and meta.has_field("event"):
		filters["event"] = event
	# A linked master is disabled rather than deleted, so a picker never offers a retired row.
	if meta.has_field("enabled"):
		filters["enabled"] = 1
	# Without permissions no query hook runs, so an unpublished row would otherwise be offered.
	if not can_read and meta.has_field("is_published"):
		filters["is_published"] = 1
	if not can_read and meta.has_field("is_hidden"):
		filters["is_hidden"] = 0

	fields = ["name"] if title_field == "name" else ["name", title_field]
	rows = frappe.get_list(
		doctype,
		filters=filters,
		fields=fields,
		limit_page_length=0 if doctype in PUBLIC_LINK_DOCTYPES else LINK_OPTION_LIMIT,
		order_by="name asc",
		ignore_permissions=not can_read,
	)
	return [{"value": row.name, "label": row.get(title_field) or row.name} for row in rows]


def is_open_reference(doctype: str, meta) -> bool:
	"""What a public form may offer someone holding no permission: published rows and masters."""
	if doctype in PUBLIC_LINK_DOCTYPES:
		return True
	return meta.has_field("is_published")


def get_auto_set_fields(form_doctype: str) -> dict[str, str]:
	sources = {"event": "from_route", "submitted_by": "session_user"}
	return {
		df.fieldname: sources[df.fieldname]
		for df in frappe.get_meta(form_doctype).fields
		if df.fieldname in sources and df.fieldtype == "Link"
	}


def get_renderable_fields(form_doctype: str, exclude_fields: set) -> dict:
	meta = frappe.get_meta(form_doctype)
	return {df.fieldname: df for df in meta.fields if is_renderable_form_field(df, exclude_fields)}


def system_exclude_fields(form_doctype: str) -> set:
	"""Fields the system sets, which no form ever asks for."""
	return STANDARD_EXCLUDE_FIELDS | set(get_auto_set_fields(form_doctype))


def is_renderable_form_field(df, exclude_fields: set) -> bool:
	if df.fieldname in exclude_fields:
		return False
	if df.fieldtype in LAYOUT_FIELDTYPES:
		return False
	return not (df.hidden or df.read_only)


def is_layout_break(df, exclude_fields: set) -> bool:
	return df.fieldtype in LAYOUT_BREAK_FIELDTYPES and df.fieldname not in exclude_fields


DEFINITION_FIELDS = (
	"label",
	"fieldname",
	"fieldtype",
	"options",
	"mandatory",
	"placeholder",
	"default_value",
	"description",
	"width",
)


def question_definition(question) -> dict:
	"""A form question as the public form and the booking page render it."""
	return {
		**{name: question.get(name) for name in DEFINITION_FIELDS},
		"order": question.idx,
	}
