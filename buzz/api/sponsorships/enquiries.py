import frappe
from frappe import _

from buzz.api.events.services import ensure_event_team_access, manageable_event
from buzz.api.filters.conditions import ListConditions, filter_field, question_fields
from buzz.api.filters.schemas import FilterField
from buzz.api.sponsorships.exceptions import EnquiryNotFound, EnquiryStatusLocked, EnquiryTierMissing
from buzz.api.sponsorships.schemas import (
	EnquiryAnswer,
	EnquiryDetail,
	EventEnquiriesResponse,
	EventEnquiryItem,
)
from buzz.api.sponsorships.services import get_tier_title

ENQUIRIES_PAGE_SIZE = 20
ENQUIRY_FIELDS = ["name", "company_name", "company_logo", "website", "status", "tier", "creation"]


def event_enquiries(
	event: str,
	search: str | None = None,
	filters: str | None = None,
	order: str = "desc",
	start: int = 0,
	limit: int = ENQUIRIES_PAGE_SIZE,
) -> EventEnquiriesResponse:
	"""One page of an event's sponsorship enquiries; Sponsorship Enquiry grants organisers no role access."""
	ensure_event_team_access(event)

	filter_fields = enquiry_filter_fields(event)
	conditions = ListConditions("Sponsorship Enquiry", filter_fields).frappe_filters(filters)
	query_filters = [["event", "=", event], *conditions]
	or_filters = search_filters(search)
	limit = max(1, min(int(limit), 100))
	start = max(0, int(start))
	# Interpolated into ORDER BY, so it can only ever be one of two literals.
	direction = "asc" if str(order).lower() == "asc" else "desc"

	rows = frappe.get_all(
		"Sponsorship Enquiry",
		filters=query_filters,
		or_filters=or_filters,
		fields=ENQUIRY_FIELDS,
		order_by=f"creation {direction}, name {direction}",
		limit_start=start,
		limit_page_length=limit,
		ignore_permissions=True,
	)
	total = frappe.db.count("Sponsorship Enquiry", {"event": event})
	matched = count_enquiries(query_filters, or_filters) if or_filters or conditions else total
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
		*question_fields(enquiry_questions(event)),
	]


def enquiry_questions(event: str) -> list:
	"""Enabled questions on the event's enquiry form; an event has at most one."""
	form = frappe.db.get_value("Sponsor Enquiry Form", {"event": event})
	if not form:
		return []
	return frappe.get_all(
		"Buzz Form Field",
		filters={"parenttype": "Sponsor Enquiry Form", "parent": form, "enabled": 1},
		fields=["fieldname", "label", "fieldtype", "options"],
		order_by="idx",
	)


def search_filters(search: str | None) -> list[list] | None:
	"""Company, contact email or website — what a manager reads off the row."""
	term = (search or "").strip()
	if not term:
		return None
	return [[field, "like", f"%{term}%"] for field in ("company_name", "contact_email", "website")]


def count_enquiries(filters: list, or_filters: list[list] | None) -> int:
	"""`frappe.db.count` takes no or_filters, so a search has to be counted the long way."""
	if not or_filters:
		return frappe.db.count("Sponsorship Enquiry", filters)
	return len(
		frappe.get_all(
			"Sponsorship Enquiry",
			filters=filters,
			or_filters=or_filters,
			pluck="name",
			ignore_permissions=True,
		)
	)


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


def tiers_by_name(names: set[str]) -> dict:
	if not names:
		return {}
	rows = frappe.get_all(
		"Sponsorship Tier",
		filters={"name": ["in", list(names)]},
		fields=["name", "title", {"prices": ["currency", "price"]}],
		ignore_permissions=True,
	)
	# Link values arrive as strings even where the tier autonames to an integer.
	return {str(row.name): row for row in rows}


def enquiry_detail(enquiry: str) -> EnquiryDetail:
	"""One enquiry for the event team; Sponsorship Enquiry grants organisers no role access."""
	event = frappe.db.get_value("Sponsorship Enquiry", enquiry, "event")
	if not event:
		EnquiryNotFound.throw()
	ensure_event_team_access(event)

	doc = frappe.get_doc("Sponsorship Enquiry", enquiry)
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


# Settled outcomes: a payment or sponsor, a removed sponsor, or the applicant's withdrawal.
LOCKED_STATUSES = ("Paid", "Cancelled", "Withdrawn")
# Moving to these tells the applicant a tier is settled, so the enquiry must carry one.
TIERED_STATUSES = ("Payment Pending", "Paid")


def set_enquiry_status(enquiry: str, status: str) -> str:
	"""Move an enquiry along for the event team; marking it paid also lists the sponsor."""
	if not frappe.db.exists("Sponsorship Enquiry", enquiry):
		EnquiryNotFound.throw()
	doc = frappe.get_doc("Sponsorship Enquiry", enquiry)
	manageable_event(doc.event)

	if doc.status in LOCKED_STATUSES and status != doc.status:
		EnquiryStatusLocked.throw()
	if status in TIERED_STATUSES and not doc.tier:
		EnquiryTierMissing.throw()
	if status == "Paid":
		doc.create_sponsor()

	doc.status = status
	doc.save(ignore_permissions=True)
	return doc.status
