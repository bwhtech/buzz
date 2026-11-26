import frappe
from frappe import _
from frappe.query_builder import Criterion

from buzz.api.events.services import ensure_event_team_access
from buzz.api.filters.conditions import ListConditions, filter_field, tags_field
from buzz.api.filters.schemas import FilterField
from buzz.api.sponsorships.enquiries import enquiry_search_criterion
from buzz.api.sponsorships.schemas import EventSponsorItem, EventSponsorsResponse
from buzz.api.tags.schemas import TagItem
from buzz.api.tags.services import tags_by_document, team_tags

SPONSOR_FIELDS = (
	"name",
	"company_name",
	"company_logo",
	"website",
	"country",
	"contact_email",
	"enquiry",
	"tier",
)


def event_sponsors(
	event: str, search: str | None = None, filters: str | None = None, order: str = "desc"
) -> EventSponsorsResponse:
	"""An event's sponsors narrowed by search and filters; few enough per event to skip paging."""
	doc = ensure_event_team_access(event, "sponsors")
	event_id = str(doc.name)
	titles = tier_titles(event_id)
	filter_fields = sponsor_filter_fields(event_id, team=doc.team, titles=titles)
	sponsor = frappe.qb.DocType("Event Sponsor")
	standard_filters, extra_criteria = ListConditions("Event Sponsor", filter_fields).split_qb_criteria(
		filters, sponsor
	)
	if search_criterion := enquiry_search_criterion(sponsor, search):
		extra_criteria.append(search_criterion)
	direction = "asc" if str(order).lower() == "asc" else "desc"
	query = frappe.qb.get_query(
		"Event Sponsor",
		fields=list(SPONSOR_FIELDS),
		filters=[["event", "=", event_id], *standard_filters],
		order_by=f"creation {direction}, name {direction}",
		ignore_permissions=True,
	)
	if extra_criteria:
		query = query.where(Criterion.all(extra_criteria))
	rows = query.run(as_dict=True)
	is_filtered = bool(standard_filters or extra_criteria)
	total = frappe.db.count("Event Sponsor", {"event": event_id}) if is_filtered else len(rows)
	return EventSponsorsResponse(
		total=total,
		sponsors=sponsor_items(rows, titles),
		filter_fields=filter_fields,
	)


def sponsor_rows(filters: list | dict, or_filters: list | None = None, direction: str = "asc") -> list:
	return frappe.get_all(
		"Event Sponsor",
		filters=filters,
		or_filters=or_filters,
		fields=list(SPONSOR_FIELDS),
		order_by=f"creation {direction}, name {direction}",
		ignore_permissions=True,
	)


def sponsor_items(rows: list, tier_titles: dict) -> list[EventSponsorItem]:
	tags = tags_by_document("Event Sponsor", [row.name for row in rows])
	return [
		EventSponsorItem(
			**row,
			tags=tags.get(row.name, []),
			tier_title=tier_titles.get(str(row.tier), row.tier) if row.tier else "",
		)
		for row in rows
	]


def tier_titles(event: str) -> dict[str, str]:
	tiers = frappe.get_all("Sponsorship Tier", {"event": event}, ["name", "title"], order_by="creation")
	return {str(tier.name): tier.title for tier in tiers}


def sponsor_filter_fields(
	event: str, team: str | None = None, titles: dict[str, str] | None = None
) -> list[FilterField]:
	resolved_titles = titles if titles is not None else tier_titles(event)
	return [
		filter_field("tier", _("Tier"), "Link", list(resolved_titles.items())),
		tags_field(sponsor_tags(event, team=team)),
	]


def sponsor_tags(event: str, team: str | None = None) -> list[TagItem]:
	"""Sponsor tags are the team's, shared by all its events."""
	resolved_team = team if team is not None else frappe.get_cached_value("Buzz Event", str(event), "team")
	return team_tags(resolved_team, "Event Sponsor")
