from collections import Counter

import frappe

from buzz.api.events.services import ensure_event_team_access
from buzz.api.sponsorships.schemas import (
	EnquiryFormState,
	EventSponsorItem,
	EventSponsorshipsResponse,
	TierItem,
)
from buzz.permissions import has_team_access

TIER_FIELDS = ["name", "title", "price", "currency", "enabled", "perks"]
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


def event_sponsorships(event: str) -> EventSponsorshipsResponse:
	"""Tiers, confirmed sponsors and the enquiry form state for one event's manage page."""
	ensure_event_team_access(event)
	doc = frappe.get_cached_doc("Buzz Event", event)

	tiers = frappe.get_all(
		"Sponsorship Tier",
		filters={"event": event},
		fields=TIER_FIELDS,
		order_by="price desc, title asc",
		ignore_permissions=True,
	)
	sponsors = frappe.get_all(
		"Event Sponsor",
		filters={"event": event},
		fields=SPONSOR_FIELDS,
		order_by="creation asc",
		ignore_permissions=True,
	)
	tier_titles = {tier.name: tier.title for tier in tiers}
	sponsor_counts = Counter(sponsor.tier for sponsor in sponsors)

	return EventSponsorshipsResponse(
		title=doc.title,
		can_write=has_team_access(doc.team, "write", frappe.session.user),
		form=form_state(doc),
		tiers=[TierItem(**tier, sponsor_count=sponsor_counts[tier.name]) for tier in tiers],
		sponsors=[
			EventSponsorItem(
				**sponsor,
				tier_title=tier_titles.get(sponsor.tier, sponsor.tier) if sponsor.tier else "",
			)
			for sponsor in sponsors
		],
	)


def form_state(doc) -> EnquiryFormState | None:
	if not frappe.db.exists("Sponsor Enquiry Form", {"event": doc.name}):
		return None
	form = frappe.get_doc("Sponsor Enquiry Form", {"event": doc.name})
	link = f"/b/{doc.route}/{form.route}" if doc.route else None
	return EnquiryFormState(name=form.name, closed=form.is_closed, link=link)
