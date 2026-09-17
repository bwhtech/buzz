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
SPONSOR_FIELDS = ["name", "company_name", "company_logo", "website", "country", "enquiry", "tier"]


def event_sponsorships(event: str) -> EventSponsorshipsResponse:
	"""Tiers, confirmed sponsors and the enquiry form state for one event's manage page."""
	ensure_event_team_access(event)
	doc = frappe.get_cached_doc("Buzz Event", event)

	tiers = frappe.get_all(
		"Sponsorship Tier",
		filters={"event": event},
		fields=TIER_FIELDS,
		order_by="price asc",
		ignore_permissions=True,
	)
	sponsors = frappe.get_all(
		"Event Sponsor",
		filters={"event": event},
		fields=SPONSOR_FIELDS,
		order_by="creation asc",
		ignore_permissions=True,
	)
	enquiry_tiers = frappe.get_all(
		"Sponsorship Enquiry",
		filters={"event": event, "tier": ["is", "set"]},
		pluck="tier",
		ignore_permissions=True,
	)

	tier_titles = {tier.name: tier.title for tier in tiers}
	sponsor_counts = Counter(sponsor.tier for sponsor in sponsors)
	enquiry_counts = Counter(enquiry_tiers)

	return EventSponsorshipsResponse(
		title=doc.title,
		can_write=has_team_access(doc.team, "write", frappe.session.user),
		form=form_state(doc),
		tiers=[
			TierItem(
				**tier,
				sponsor_count=sponsor_counts[tier.name],
				enquiry_count=enquiry_counts[tier.name],
			)
			for tier in tiers
		],
		sponsors=[
			EventSponsorItem(**sponsor, tier_title=tier_title_of(sponsor.tier, tier_titles))
			for sponsor in sponsors
		],
	)


def tier_title_of(tier: str | None, tier_titles: dict[str, str]) -> str:
	return tier_titles.get(tier, tier) if tier else ""


def form_state(doc) -> EnquiryFormState | None:
	name = frappe.db.get_value("Sponsor Enquiry Form", {"event": doc.name})
	if not name:
		return None
	form = frappe.get_doc("Sponsor Enquiry Form", name)
	link = f"/b/{doc.route}/{form.route}" if doc.route else None
	return EnquiryFormState(name=form.name, closed=form.is_closed, link=link)
