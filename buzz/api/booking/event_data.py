from typing import TYPE_CHECKING

import frappe
from frappe import _

from buzz.api.booking.cache import EventBookingCache
from buzz.api.booking.exceptions import InvalidAccessCode
from buzz.api.booking.schemas import AccessCodeStatus, EventBookingDataResponse, TaxSettings
from buzz.api.filters.conditions import QUESTION_FIELDS
from buzz.api.forms.conditions import parse_rules
from buzz.api.forms.fields import question_definition
from buzz.events.doctype.buzz_form.form_types import (
	APPLIED_TO_BY_FORM_DOCTYPE,
	REGISTRATION_FORM_DOCTYPE,
	form_type,
	is_registration_closed,
)
from buzz.payments import get_payment_gateways_for_event
from buzz.permissions import can_add_guests_directly
from buzz.ticketing.doctype.buzz_coupon_code.buzz_coupon_code import BuzzCouponCode
from buzz.ticketing.doctype.event_ticket_category.event_ticket_category import get_ordered_categories
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import (
	remaining_for,
	sold_counts,
	waitlist_ticket_types,
)
from buzz.ticketing.doctype.ticket_add_on.ticket_add_on import add_on_options
from buzz.ticketing.doctype.ticket_hold.ticket_hold import held_quantities

if TYPE_CHECKING:
	from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent

PUBLIC_TICKET_TYPE_FIELDS = (
	"name",
	"title",
	"description",
	"category",
	"event",
	"is_published",
	"is_hidden",
	"auto_unpublish_after",
	"max_tickets_available",
	"requires_approval",
	"enable_waitlist",
)
PUBLIC_PRICE_FIELDS = ("name", "parent", "parentfield", "parenttype", "idx", "currency", "price")
PUBLIC_ADD_ON_FIELDS = (
	"name",
	"title",
	"event",
	"price",
	"currency",
	"description",
	"enabled",
	"user_selects_option",
	"options",
)


def build_event_booking_data(
	event_route: str, hold_token: str | None = None, access_code: str | None = None
) -> EventBookingDataResponse:
	event_name = EventBookingCache.get_event_id_by_route(event_route)
	if not event_name:
		frappe.throw(_("Event not found"), frappe.DoesNotExistError)
	event_doc = frappe.get_cached_doc("Buzz Event", str(event_name))

	if not event_doc.is_published:
		frappe.throw(_("Event not found"), frappe.DoesNotExistError)

	event_id = str(event_doc.name)
	metadata = get_event_booking_metadata(event_id)
	offline_methods = metadata["offline_methods"]
	payment_gateways = [
		*get_payment_gateways_for_event(event_id, event_doc=event_doc),
		*(method["title"] for method in offline_methods),
	]

	categories = metadata["categories"]
	coupon = BuzzCouponCode.find_available_access_code(event_id, access_code)
	unlocked = coupon.unlocked_ticket_types() if coupon else set()
	ticket_types, remaining_by_type, waitlisted_types = load_available_ticket_type_rows(
		event_doc, categories, hold_token, unlocked, published_ticket_types=metadata["ticket_types"]
	)
	adds_guests_directly = can_add_guests_directly(event_id, frappe.session.user, team=event_doc.team or "")
	form_data = metadata["form_data"]

	return EventBookingDataResponse(
		registrations_closed=is_registration_closed(form_data["reg_form"], event_doc),
		event_details=get_event_details(event_doc),
		available_ticket_types=[
			ticket_type_dict_row(
				row,
				adds_guests_directly,
				remaining=remaining_by_type[str(row.name)],
				waitlisted=str(row.name) in waitlisted_types,
				event_requires_approval=bool(event_doc.requires_approval),
			)
			for row in ticket_types
		],
		ticket_categories=categories_in_use(categories, ticket_types),
		available_add_ons=metadata["add_ons"],
		tax_settings=TaxSettings(
			apply_tax=event_doc.apply_tax,
			tax_inclusive=event_doc.tax_inclusive,
			tax_label=event_doc.tax_label or "Tax",
			tax_percentage=event_doc.tax_percentage or 0,
		),
		custom_fields=form_data["custom_fields"],
		core_fields=form_data["core_fields"],
		success=form_data["success"],
		logic_rules=form_data["logic_rules"],
		payment_gateways=payment_gateways,
		offline_payment_enabled=len(offline_methods) > 0,
		offline_methods=offline_methods,
		access_code=access_code_status(access_code, coupon),
	)


def get_event_booking_metadata(event_id: str | int) -> dict:
	return EventBookingCache.get_metadata(event_id, load_event_booking_metadata)


def load_event_booking_metadata(event_id: str) -> dict:
	"""Load static per-event booking configuration from DB for Redis caching."""
	return {
		"ticket_types": load_published_ticket_types_with_prices(event_id),
		"categories": get_ordered_categories(event_id),
		"add_ons": get_available_add_ons(event_id),
		"offline_methods": get_offline_methods(event_id),
		"form_data": load_registration_form_metadata(event_id),
	}


def load_published_ticket_types_with_prices(event_id: str) -> list[frappe._dict]:
	tt = frappe.qb.DocType("Event Ticket Type")
	rows = (
		frappe.qb.from_(tt)
		.select(*(tt[field] for field in PUBLIC_TICKET_TYPE_FIELDS))
		.where((tt.event == event_id) & (tt.is_published == 1))
		.orderby(tt.creation, order=frappe.qb.desc)
	).run(as_dict=True)
	if not rows:
		return []

	price = frappe.qb.DocType("Buzz Price")
	price_rows = (
		frappe.qb.from_(price)
		.select(*(price[field] for field in PUBLIC_PRICE_FIELDS))
		.where(
			(price.parenttype == "Event Ticket Type")
			& (price.parentfield == "prices")
			& price.parent.isin([str(row.name) for row in rows])
		)
		.orderby(price.idx)
	).run(as_dict=True)
	prices_by_parent: dict[str, list[frappe._dict]] = {}
	for price_row in price_rows:
		cleaned = frappe._dict({k: v for k, v in price_row.items() if v is not None}, doctype="Buzz Price")
		prices_by_parent.setdefault(str(price_row.parent), []).append(cleaned)
	for row in rows:
		row["prices"] = prices_by_parent.get(str(row.name), [])
	return rows


def access_code_status(access_code: str | None, coupon: BuzzCouponCode | None) -> AccessCodeStatus:
	if coupon:
		return AccessCodeStatus(code=coupon.code)
	return AccessCodeStatus(error=str(InvalidAccessCode.message) if access_code else None)


def get_event_details(event_doc: "BuzzEvent"):
	return {
		"name": event_doc.name,
		"title": event_doc.title,
		"route": event_doc.route,
		"start_date": event_doc.start_date,
		"end_date": event_doc.end_date,
		"start_time": event_doc.start_time,
		"end_time": event_doc.end_time,
		"time_zone": event_doc.time_zone,
		"time_zone_label": event_doc.time_zone_label,
		"venue": event_doc.venue,
		"venue_name": event_doc.get_venue_name(),
		"medium": event_doc.medium,
		"category": event_doc.category,
		"banner_image": event_doc.banner_image,
		"short_description": event_doc.short_description,
		"free_event": event_doc.free_event,
		"send_ticket_email": event_doc.send_ticket_email,
		"allow_guest_booking": event_doc.allow_guest_booking,
		"guest_verification_method": event_doc.guest_verification_method,
		"default_ticket_type": event_doc.default_ticket_type,
		"requires_approval": event_doc.requires_approval,
		"enable_waitlist": event_doc.enable_waitlist,
	}


def load_available_ticket_type_rows(
	event_doc: "BuzzEvent",
	categories: list[dict] | None = None,
	hold_token: str | None = None,
	unlocked: set[str] | None = None,
	*,
	published_ticket_types: list[frappe._dict] | None = None,
) -> tuple[list[frappe._dict], dict[str, int], set[str]]:
	"""Published, visible ticket type rows with prices and live batched availability."""
	event_id = str(event_doc.name)
	rows = (
		published_ticket_types
		if published_ticket_types is not None
		else get_event_booking_metadata(event_id)["ticket_types"]
	)

	unlocked_ids = unlocked or set()
	candidates = [row for row in rows if not row.is_hidden or str(row.name) in unlocked_ids]
	if not candidates:
		return [], {}, set()

	limited_names = [str(row.name) for row in candidates if row.max_tickets_available]
	sold = sold_counts(limited_names, event=event_id)
	held = held_quantities(limited_names, hold_token)
	event_waitlist = bool(event_doc.enable_waitlist)

	available = []
	remaining_by_type: dict[str, int] = {}
	waitlist_candidates: list[str] = []
	for row in candidates:
		key = str(row.name)
		remaining = remaining_for(row, sold, held)
		has_waitlist = bool(row.max_tickets_available and (row.enable_waitlist or event_waitlist))
		if has_waitlist or remaining == -1 or remaining >= 1:
			available.append(row)
			remaining_by_type[key] = remaining
			if has_waitlist:
				waitlist_candidates.append(key)

	if not available:
		return [], {}, set()

	queued = waitlist_ticket_types(event_id, waitlist_candidates) if waitlist_candidates else set()
	waitlisted_types = {key for key in waitlist_candidates if remaining_by_type[key] < 1 or key in queued}

	position = {category["name"]: index for index, category in enumerate(categories or [])}
	ordered = sorted(available, key=lambda row: position.get(row.category, len(position)))
	return ordered, remaining_by_type, waitlisted_types


def ticket_type_dict_row(
	row: frappe._dict,
	adds_guests_directly: bool,
	*,
	remaining: int,
	waitlisted: bool,
	event_requires_approval: bool,
) -> frappe._dict:
	out = frappe._dict({k: v for k, v in row.items() if v is not None and k != "tickets_sold"})
	out["doctype"] = "Event Ticket Type"
	out["remaining_tickets"] = remaining
	out["needs_approval"] = (
		bool(row.requires_approval or event_requires_approval) and not adds_guests_directly
	)
	out["waitlisted"] = waitlisted
	return out


def load_registration_form_metadata(event_id: str) -> dict:
	"""Read both registration Buzz Forms and all their fields in one LEFT JOIN query."""
	form = frappe.qb.DocType("Buzz Form")
	field = frappe.qb.DocType("Buzz Form Field")
	rows = (
		frappe.qb.from_(form)
		.left_join(field)
		.on((field.parent == form.name) & (field.parenttype == "Buzz Form"))
		.select(
			form.name.as_("form_name"),
			form.form_doctype,
			form.publish,
			form.auto_close_at,
			form.success_title,
			form.success_message,
			form.logic_rules,
			field.name.as_("field_row_name"),
			field.is_standard,
			*(field[name] for name in QUESTION_FIELDS),
		)
		.where((form.event == str(event_id)) & form.form_doctype.isin(list(APPLIED_TO_BY_FORM_DOCTYPE)))
		.orderby(field.idx)
	).run(as_dict=True)

	by_doctype: dict[str, frappe._dict] = {}
	fields_by_parent: dict[str, list] = {}
	for row in rows:
		doctype = row.form_doctype
		if doctype not in by_doctype:
			by_doctype[doctype] = frappe._dict(
				name=row.form_name,
				form_doctype=doctype,
				publish=row.publish,
				auto_close_at=row.auto_close_at,
				success_title=row.success_title,
				success_message=row.success_message,
				logic_rules=row.logic_rules,
			)
		if row.field_row_name:
			fields_by_parent.setdefault(row.form_name, []).append(row)

	reg_form = by_doctype.get(REGISTRATION_FORM_DOCTYPE)
	custom_fields: list[dict] = []
	core_fields: dict[str, list[dict]] = {}
	logic_rules: dict[str, list] = {}

	for form_doctype, applied_to in APPLIED_TO_BY_FORM_DOCTYPE.items():
		form_row = by_doctype.get(form_doctype)
		form_fields = fields_by_parent.get(form_row.name, []) if form_row else []
		for row in form_fields:
			if row.enabled and not row.is_standard:
				custom_fields.append({**question_definition(row), "applied_to": applied_to})
		standard_rows = [
			{"fieldname": row.fieldname, "label": row.label, "width": row.width, "enabled": row.enabled}
			for row in form_fields
			if row.is_standard
		]
		core_fields[applied_to] = standard_rows or [
			{"fieldname": fieldname, "label": label, "width": "Half", "enabled": 1}
			for fieldname, label in form_type(form_doctype).core_fields.items()
		]
		logic_rules[applied_to] = parse_rules(form_row.logic_rules if form_row else None)

	return {
		"reg_form": (
			frappe._dict(publish=reg_form.publish, auto_close_at=reg_form.auto_close_at) if reg_form else None
		),
		"custom_fields": custom_fields,
		"core_fields": core_fields,
		"success": {
			"title": reg_form.success_title if reg_form else None,
			"message": reg_form.success_message if reg_form else None,
		},
		"logic_rules": logic_rules,
	}


def categories_in_use(categories: list[dict], ticket_types: list) -> list[dict]:
	used = {ticket_type.category for ticket_type in ticket_types}
	return [category for category in categories if category["name"] in used]


def get_available_add_ons(event_id: str | int) -> list:
	addon = frappe.qb.DocType("Ticket Add-on")
	add_ons = (
		frappe.qb.from_(addon)
		.select(*(addon[field] for field in PUBLIC_ADD_ON_FIELDS))
		.where((addon.event == str(event_id)) & (addon.enabled == 1))
		.orderby(addon.title)
	).run(as_dict=True)
	if not add_ons:
		return []
	scope = frappe.qb.DocType("Ticket Add-on Ticket Type")
	scope_rows = (
		frappe.qb.from_(scope)
		.select(scope.parent, scope.ticket_type)
		.where((scope.parenttype == "Ticket Add-on") & scope.parent.isin([row.name for row in add_ons]))
		.orderby(scope.idx)
	).run(as_dict=True)
	by_parent: dict[str, list[str]] = {}
	for row in scope_rows:
		by_parent.setdefault(row.parent, []).append(str(row.ticket_type))
	for add_on in add_ons:
		add_on.ticket_types = by_parent.get(add_on.name, [])
		if add_on.user_selects_option:
			add_on.options = add_on_options(add_on.options)
	return add_ons


def get_registration_success(event_id: str) -> dict:
	"""The organiser's own title and message for a finished booking."""
	return frappe.db.get_value(
		"Buzz Form",
		{"event": str(event_id), "form_doctype": REGISTRATION_FORM_DOCTYPE},
		["success_title as title", "success_message as message"],
		as_dict=True,
	) or {"title": None, "message": None}


def get_custom_fields(event_id: str, applied_to: str, offline_payment_method: str | None = None) -> list:
	filters = {"event": str(event_id), "enabled": 1, "applied_to": applied_to}
	if offline_payment_method:
		filters["offline_payment_method"] = str(offline_payment_method)
	return frappe.db.get_all("Buzz Custom Field", filters=filters, fields=["*"], order_by="order")


def get_offline_methods(event_id: str | int) -> list:
	event_id = str(event_id)
	method_table = frappe.qb.DocType("Offline Payment Method")
	methods = (
		frappe.qb.from_(method_table)
		.select(
			method_table.name,
			method_table.title,
			method_table.description,
			method_table.collect_payment_proof,
		)
		.where((method_table.event == event_id) & (method_table.enabled == 1))
		.orderby(method_table.creation)
	).run(as_dict=True)
	if not methods:
		return []
	fields_by_method: dict[str, list] = {}
	method_ids = [str(method.name) for method in methods]
	rows = frappe.db.get_all(
		"Buzz Custom Field",
		filters={
			"event": event_id,
			"enabled": 1,
			"applied_to": "Offline Payment Form",
			"offline_payment_method": ["in", method_ids],
		},
		fields=["*"],
		order_by="order",
	)
	for row in rows:
		fields_by_method.setdefault(str(row.offline_payment_method), []).append(row)
	return [
		{
			"name": method.name,
			"title": method.title,
			"description": method.description,
			"collect_payment_proof": method.collect_payment_proof,
			"custom_fields": fields_by_method.get(str(method.name), []),
		}
		for method in methods
	]
