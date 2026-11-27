import frappe
from frappe import _
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Count

from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.events.services import ensure_event_team_access
from buzz.api.filters.conditions import ListConditions, filter_field, form_questions, question_fields
from buzz.api.filters.schemas import FilterField
from buzz.api.sponsorships.exceptions import EnquiryNotFound, EnquiryStatusLocked, EnquiryTierMissing
from buzz.api.sponsorships.schemas import (
	EnquiryAnswer,
	EnquiryDetail,
	EventEnquiriesResponse,
	EventEnquiryItem,
)
from buzz.api.sponsorships.services import LOCKED_STATUSES, get_tier_title, tiers_by_name
from buzz.permissions import has_section_permission

ENQUIRIES_PAGE_SIZE = 20
ENQUIRY_FIELDS = ("name", "company_name", "company_logo", "website", "status", "tier", "creation")


def event_enquiries(
	event: str,
	search: str | None = None,
	filters: str | None = None,
	order: str = "desc",
	start: int = 0,
	limit: int = ENQUIRIES_PAGE_SIZE,
) -> EventEnquiriesResponse:
	"""One page of an event's sponsorship enquiries; Sponsorship Enquiry grants organisers no role access."""
	doc = ensure_event_team_access(event, "sponsors")
	event_id = str(doc.name)

	filter_fields = enquiry_filter_fields(event_id)
	enquiry = frappe.qb.DocType("Sponsorship Enquiry")
	standard_filters, extra_criteria = ListConditions(
		"Sponsorship Enquiry", filter_fields, event=event_id
	).split_qb_criteria(filters, enquiry)
	if search_criterion := enquiry_search_criterion(enquiry, search):
		extra_criteria.append(search_criterion)
	limit = max(1, min(int(limit), 100))
	start = max(0, int(start))
	direction = "asc" if str(order).lower() == "asc" else "desc"

	base_filters = [["event", "=", event_id], *standard_filters]
	query = frappe.qb.get_query(
		"Sponsorship Enquiry",
		fields=list(ENQUIRY_FIELDS),
		filters=base_filters,
		order_by=f"creation {direction}, name {direction}",
		limit=limit,
		offset=start,
		ignore_permissions=True,
	)
	if extra_criteria:
		query = query.where(Criterion.all(extra_criteria))
	rows = query.run(as_dict=True)
	is_filtered = bool(standard_filters or extra_criteria)
	total = (
		len(rows)
		if not is_filtered and start == 0 and len(rows) < limit
		else frappe.db.count("Sponsorship Enquiry", {"event": event_id})
	)
	if not is_filtered:
		matched = total
	elif start == 0 and len(rows) < limit:
		matched = len(rows)
	else:
		count_query = frappe.qb.get_query(
			"Sponsorship Enquiry",
			fields=[Count(enquiry.name)],
			filters=base_filters,
			ignore_permissions=True,
		)
		if extra_criteria:
			count_query = count_query.where(Criterion.all(extra_criteria))
		count_rows = count_query.run()
		matched = count_rows[0][0] if count_rows else 0
	return EventEnquiriesResponse(
		total=total,
		matched=matched,
		enquiries=enquiry_items(rows),
		has_next_page=start + len(rows) < matched,
		filter_fields=filter_fields,
	)


def enquiry_filter_fields(event: str) -> list[FilterField]:
	"""What an enquiry list can be narrowed by: its own fields, then the form's questions."""
	statuses = frappe.get_meta("Sponsorship Enquiry").get_field("status").options.splitlines()
	tiers = frappe.get_all("Sponsorship Tier", {"event": event}, ["name", "title"], order_by="creation")
	return [
		filter_field("status", _("Status"), "Select", [(status, _(status)) for status in statuses]),
		filter_field("tier", _("Tier"), "Link", [(str(tier.name), tier.title) for tier in tiers]),
		filter_field("contact_email", _("Contact email"), "Email"),
		*question_fields(form_questions(event, "Sponsorship Enquiry")),
	]


def enquiry_search_criterion(table, search: str | None):
	term = (search or "").strip()
	if not term:
		return None
	pattern = f"%{term}%"
	return table.company_name.like(pattern) | table.contact_email.like(pattern) | table.website.like(pattern)


def search_filters(search: str | None) -> list[list] | None:
	"""Company, contact email or website — what a manager reads off the row."""
	term = (search or "").strip()
	if not term:
		return None
	return [[field, "like", f"%{term}%"] for field in ("company_name", "contact_email", "website")]


def enquiry_items(rows: list) -> list[EventEnquiryItem]:
	tiers = tiers_by_name({row.tier for row in rows if row.tier})
	return [enquiry_item(row, tiers.get(str(row.tier))) for row in rows]


def enquiry_item(row, tier) -> EventEnquiryItem:
	return EventEnquiryItem(
		**row,
		tier_title=(tier.title if tier else row.tier) or "",
		tier_price=tier.prices[0].price if tier else None,
		tier_currency=tier.prices[0].currency if tier else None,
	)


def enquiry_detail(enquiry: str) -> EnquiryDetail:
	"""One enquiry for the event team; Sponsorship Enquiry grants organisers no role access."""
	try:
		doc = frappe.get_doc("Sponsorship Enquiry", enquiry)
	except frappe.DoesNotExistError:
		frappe.clear_last_message()
		EnquiryNotFound.throw()
	ensure_event_team_access(doc.event, "sponsors")

	return EnquiryDetail(
		name=doc.name,
		company_name=doc.company_name,
		company_logo=doc.company_logo,
		status=doc.status,
		tier=doc.tier,
		tier_title=get_tier_title(doc.tier) if doc.tier else "",
		website=doc.website,
		country=doc.country,
		phone=doc.phone,
		contact=doc.contact_recipient,
		creation=doc.creation,
		modified=doc.modified,
		sponsor=frappe.db.get_value("Event Sponsor", {"enquiry": doc.name}),
		answers=[
			EnquiryAnswer(label=row.label or row.fieldname, value=row.value, fieldtype=row.fieldtype)
			for row in doc.additional_fields
		],
	)


# Moving to these tells the applicant a tier is settled, so the enquiry must carry one.
TIERED_STATUSES = ("Payment Pending", "Paid")


def set_enquiry_status(enquiry: str, status: str) -> str:
	"""Move an enquiry along for the event team; marking it paid also lists the sponsor."""
	try:
		doc = frappe.get_doc("Sponsorship Enquiry", enquiry)
	except frappe.DoesNotExistError:
		frappe.clear_last_message()
		EnquiryNotFound.throw()
	event_doc = ensure_event_team_access(doc.event, "sponsors")
	if not has_section_permission(
		doc.event, "sponsors", "write", frappe.session.user, team=event_doc.team or ""
	):
		CannotManageEvent.throw()

	if doc.status in LOCKED_STATUSES and status != doc.status:
		EnquiryStatusLocked.throw()
	if status in TIERED_STATUSES and not doc.tier:
		EnquiryTierMissing.throw()
	if status == "Paid":
		doc.create_sponsor()

	doc.status = status
	doc.save(ignore_permissions=True)
	return doc.status
