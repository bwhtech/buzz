import frappe
from frappe import _

from buzz.api.events.services import ensure_event_team_access
from buzz.api.filters.conditions import ListConditions, filter_field, tags_field
from buzz.api.filters.schemas import FilterField
from buzz.api.sponsorships.enquiries import search_filters
from buzz.api.sponsorships.schemas import EventSponsorItem, EventSponsorsResponse
from buzz.api.tags.schemas import TagItem
from buzz.api.tags.services import tags_by_document, team_tags

SPONSOR_FIELDS = [
	"name",
	"company_name",
	"company_logo",
	"website",
	"country",
	"contact_email",
	"enquiry",
	"tier",
]


def event_sponsors(
	event: str, search: str | None = None, filters: str | None = None, order: str = "desc"
) -> EventSponsorsResponse:
	"""An event's sponsors narrowed by search and filters; few enough per event to skip paging."""
	ensure_event_team_access(event)
	filter_fields = sponsor_filter_fields(event)
	conditions = ListConditions("Event Sponsor", filter_fields).frappe_filters(filters)
	# Interpolated into ORDER BY, so it can only ever be one of two literals.
	direction = "asc" if str(order).lower() == "asc" else "desc"
	rows = sponsor_rows([["event", "=", event], *conditions], search_filters(search), direction)
	return EventSponsorsResponse(
		total=frappe.db.count("Event Sponsor", {"event": event}),
		sponsors=sponsor_items(rows, tier_titles(event)),
		filter_fields=filter_fields,
	)


def sponsor_rows(filters: list, or_filters: list | None = None, direction: str = "asc") -> list:
	return frappe.get_all(
		"Event Sponsor",
		filters=filters,
		or_filters=or_filters,
		fields=SPONSOR_FIELDS,
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


def sponsor_filter_fields(event: str) -> list[FilterField]:
	return [
		filter_field("tier", _("Tier"), "Link", list(tier_titles(event).items())),
		tags_field(sponsor_tags(event)),
	]


def sponsor_tags(event: str) -> list[TagItem]:
	"""Sponsor tags are the team's, shared by all its events."""
	return team_tags(frappe.db.get_value("Buzz Event", event, "team"), "Event Sponsor")
