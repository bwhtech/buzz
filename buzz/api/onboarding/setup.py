"""Records the onboarding steps create: the user's community and their first event draft."""

from datetime import datetime, timedelta

import frappe

from buzz.api.communities.creation import create_community, ensure_communities_enabled
from buzz.api.events.exceptions import CannotCreateEvents
from buzz.api.exceptions import NotPermitted
from buzz.api.onboarding.schemas import CommunityDraft, EventDraft, FirstEvent
from buzz.api.teams import public_page
from buzz.permissions import has_team_access

DEFAULT_CATEGORY = "Meetups"
DRAFT_LENGTH = timedelta(hours=1)


def owned_community(user: str) -> str | None:
	owned = frappe.get_all(
		"Buzz Team Membership", filters={"user": user, "team_role": "Owner", "enabled": 1}, pluck="team"
	)
	if not owned:
		return None
	return frappe.db.get_value(
		"Buzz Team", {"name": ("in", owned), "is_personal": 0}, order_by="creation desc"
	)


def community_draft(user: str) -> CommunityDraft | None:
	team = owned_community(user)
	if not team:
		return None
	row = frappe.db.get_value(
		"Buzz Team", team, ["name", "team_name", "slug", "logo", "short_description"], as_dict=True
	)
	return CommunityDraft(**row)


def save_community(user: str, team_name: str, slug: str, logo: str, short_description: str) -> str:
	ensure_communities_enabled()
	team = owned_community(user) or create_community(team_name, slug).team
	doc = frappe.get_doc("Buzz Team", team)
	public_page.set_slug(doc, slug)
	doc.update({"team_name": team_name, "logo": logo, "short_description": short_description})
	doc.save(ignore_permissions=True)
	return doc.name


def event_draft(user: str) -> EventDraft | None:
	row = frappe.db.get_value(
		"Buzz Event",
		{"owner": user, "is_published": 0},
		["name", "team", "title", "start_date", "start_time", "medium", "venue"],
		as_dict=True,
		order_by="creation desc",
	)
	if not row:
		return None
	venue = row.pop("venue")
	row.update(
		name=str(row.name),
		start_time=str(row.start_time),
		venue_name=frappe.db.get_value("Event Venue", venue, "venue_name") if venue else None,
	)
	return EventDraft(**row)


def save_first_event(new: FirstEvent) -> str:
	user = frappe.session.user
	if not has_team_access(new.team, "create", user):
		CannotCreateEvents.throw()
	doc = draft_to_edit(new.event, user) or frappe.new_doc(
		"Buzz Event", category=DEFAULT_CATEGORY, is_published=0
	)
	end = datetime.combine(new.start_date, datetime.min.time()) + new.start_time + DRAFT_LENGTH
	doc.update(
		{
			"team": new.team,
			"title": new.title,
			"start_date": new.start_date,
			"start_time": new.start_time,
			"end_date": end.date(),
			"end_time": end - datetime.combine(end.date(), datetime.min.time()),
			"medium": new.medium,
			"venue": venue_for(new.team, new.venue_name) if new.medium == "In Person" else None,
			"time_zone": frappe.db.get_value("User", user, "time_zone"),
		}
	)
	doc.save()
	return str(doc.name)


def draft_to_edit(event: str | None, user: str):
	if not event:
		return None
	doc = frappe.get_doc("Buzz Event", event)
	if doc.owner != user or doc.is_published or not has_team_access(doc.team, "write", user):
		NotPermitted.throw()
	return doc


def venue_for(team: str, venue_name: str | None) -> str | None:
	if not venue_name:
		return None
	filters = {"team": team, "venue_name": venue_name}
	if existing := frappe.db.get_value("Event Venue", filters):
		return existing
	# The name doubles as the address until the host adds a real one in the full editor.
	venue = frappe.get_doc({"doctype": "Event Venue", **filters, "address": venue_name})
	return venue.insert(ignore_permissions=True).name
