import textwrap
from collections import defaultdict
from datetime import datetime
from functools import cached_property
from itertools import groupby

import frappe
from frappe import _
from frappe.utils import date_diff, flt, format_date, get_datetime, get_time, get_url, getdate, today

from buzz.api.booking.services import are_registrations_closed
from buzz.api.communities.queries import time_of_day
from buzz.api.maps.services import place_search_enabled
from buzz.events.doctype.buzz_team.team_map import TeamMap
from buzz.events.doctype.community_event_request.community_event_request import approved_external_requests
from buzz.permissions import role_allows, team_role_of
from buzz.www.event.date_range import format_time
from buzz.www.event.index import public_links
from buzz.www.event.meta import DESCRIPTION_LENGTH, plain_text
from buzz.www.events import (
	CARD_FIELDS,
	LISTING_LIMIT,
	TIME_FIELDS,
	exclude_ended_events,
	has_ended,
	has_started,
	upcoming_filters,
)

PAST_LIMIT = 30
VENUE_FIELDS = [
	"venue.latitude as latitude",
	"venue.longitude as longitude",
	"venue.city as city",
	"venue.venue_country as country",
]
# A community lists other teams' events too, so each card names its event's own team.
HOST_FIELDS = ["team.team_name as host_name", "team.logo as host_logo"]
EVENT_FIELDS = CARD_FIELDS + TIME_FIELDS + VENUE_FIELDS + HOST_FIELDS + ["name", "registrations_close_at"]


def day_labels(day) -> dict:
	relative = {0: _("Today"), 1: _("Tomorrow")}.get(date_diff(day, today()))
	return {"label": relative or format_date(day, "d MMM"), "weekday": format_date(day, "EEEE")}


def group_by_day(cards: list[dict]) -> list[dict]:
	return [
		{"date": date, **day_labels(getdate(date)), "events": list(group)}
		for date, group in groupby(cards, key=lambda card: card["date"])
	]


def co_host_names_by_event(events: list[str]) -> dict[str, list[str]]:
	"""Co-host names per event, in table order, for every card in one query."""
	if not events:
		return {}
	co_host, host = frappe.qb.DocType("Event CoHost"), frappe.qb.DocType("Event Host")
	rows = (
		frappe.qb.from_(co_host)
		.join(host)
		.on(host.name == co_host.host)
		.select(co_host.parent, host.host_name)
		.where((co_host.parenttype == "Buzz Event") & co_host.parent.isin(events))
		.orderby(co_host.idx)
	).run(as_dict=True)
	names = defaultdict(list)
	for row in rows:
		names[row.parent].append(row.host_name)
	return names


def starts_at(event) -> datetime:
	return datetime.combine(getdate(event.start_date), get_time(event.start_time))


def external_event(request) -> frappe._dict:
	"""An approved external request in the shape of a Buzz Event row."""
	start, end = get_datetime(request.start_datetime), get_datetime(request.end_datetime)
	return frappe._dict(
		name=request.name,
		title=request.event_title,
		event_url=request.event_url,
		host_name=request.host,
		venue_name=request.event_location,
		start_date=start.date(),
		start_time=time_of_day(start),
		end_date=end.date(),
		end_time=time_of_day(end),
		is_external=True,
	)


def external_card(event) -> dict:
	"""Opens the host's own page; it has no image or coordinates, so it stays off the map."""
	return {
		"route": event.name,
		"date": str(event.start_date),
		"title": event.title,
		"url": event.event_url,
		"is_external": True,
		"image": None,
		"time": format_time(event.start_time),
		"host_names": event.host_name,
		"host_logo": None,
		"place": event.venue_name,
		"is_online": False,
		"is_live": has_started(event) and not has_ended(event),
		"is_attending": False,
		"registrations_closed": False,
		"city": None,
		"country": None,
		"latitude": None,
		"longitude": None,
	}


class TeamPage:
	"""Context for a team's public page: identity, links and its own event timeline."""

	def __init__(self, team):
		self.team = team

	def as_context(self) -> dict:
		upcoming = [self.card(event) for event in self.upcoming_events]
		past = [self.card(event) for event in self.past_events]
		return {
			"title": self.team.team_name,
			"links": public_links(self.team.links),
			"events_hosted": frappe.db.count("Buzz Event", {"team": self.team.name, "is_published": 1}),
			"upcoming_days": group_by_day(upcoming),
			"past_days": group_by_day(past),
			"meta": self.meta(),
			"is_guest": frappe.session.user == "Guest",
			"is_organizer": self.is_organizer(),
			"manage_url": self.manage_url(),
			"place_search_enabled": place_search_enabled(),
			**TeamMap(upcoming, past).as_context(),
		}

	@cached_property
	def upcoming_events(self) -> list:
		events = frappe.get_all(
			"Buzz Event",
			filters=upcoming_filters(),
			or_filters=self.event_filters(),
			fields=EVENT_FIELDS,
			order_by="start_date asc, start_time asc",
			limit=LISTING_LIMIT,
		)
		external = exclude_ended_events(self.external_events)
		return sorted(exclude_ended_events(events) + external, key=starts_at)[:LISTING_LIMIT]

	@cached_property
	def past_events(self) -> list:
		# By start date: a one-day event leaves end_date blank, and has_ended makes the exact cut.
		events = frappe.get_all(
			"Buzz Event",
			filters={"is_published": 1, "route": ["is", "set"], "start_date": ["<=", today()]},
			or_filters=self.event_filters(),
			fields=EVENT_FIELDS,
			order_by="start_date desc, start_time desc",
			limit=PAST_LIMIT,
		)
		ended = [event for event in events + self.external_events if has_ended(event)]
		return sorted(ended, key=starts_at, reverse=True)[:PAST_LIMIT]

	@cached_property
	def external_events(self) -> list:
		if not self.team.accept_community_submissions:
			return []
		return [external_event(request) for request in approved_external_requests(self.team.name)]

	@cached_property
	def buzz_event_names(self) -> list[str]:
		return [str(event.name) for event in self.upcoming_events + self.past_events if not event.is_external]

	@cached_property
	def co_host_names(self) -> dict[str, list[str]]:
		return co_host_names_by_event(self.buzz_event_names)

	@cached_property
	def attending_events(self) -> set[str]:
		"""Events the visitor holds a ticket for: the dashboard's Attending rule."""
		events = self.buzz_event_names
		if frappe.session.user == "Guest" or not events:
			return set()
		tickets = {"attendee_email": frappe.session.user, "docstatus": 1, "event": ["in", events]}
		return set(frappe.get_all("Event Ticket", filters=tickets, pluck="event"))

	def event_filters(self) -> dict:
		"""The team's own events, plus those its community approved."""
		filters = {"team": self.team.name}
		if self.team.accept_community_submissions:
			approved = {"community": self.team.name, "status": "Approved"}
			filters["name"] = [
				"in",
				frappe.get_all("Community Event Request", filters=approved, pluck="event"),
			]
		return filters

	def card(self, event) -> dict:
		if event.is_external:
			return external_card(event)
		is_online = event.medium == "Online"
		has_location = not is_online and bool(flt(event.latitude) and flt(event.longitude))
		return {
			"route": event.route,
			"date": str(getdate(event.start_date)),
			"title": event.title,
			"url": f"/events/{event.route}",
			"image": event.card_image or event.banner_image,
			"time": format_time(event.start_time),
			"host_names": ", ".join([event.host_name, *self.co_host_names.get(str(event.name), [])]),
			"host_logo": event.host_logo,
			"place": _("Online") if is_online else event.venue_name,
			"is_online": is_online,
			"is_live": has_started(event) and not has_ended(event),
			"is_attending": str(event.name) in self.attending_events,
			# Past events have ended, so only upcoming cards can say this.
			"registrations_closed": not has_ended(event) and are_registrations_closed(event),
			"city": event.city,
			"country": event.country,
			"latitude": flt(event.latitude) if has_location else None,
			"longitude": flt(event.longitude) if has_location else None,
		}

	def manage_url(self) -> str | None:
		if frappe.has_permission("Buzz Team", "write", self.team):
			return f"/b/manage/communities/{self.team.name}"

	def is_organizer(self) -> bool:
		"""The community's own curators add events straight away; anyone else submits them.

		Membership, not access: a System Manager outside the team still submits from here.
		"""
		team_role = team_role_of(frappe.session.user, self.team.name)
		return bool(team_role) and role_allows(team_role, "write")

	def meta(self) -> dict:
		text = self.team.short_description or plain_text(self.team.about)
		return {
			"url": get_url(f"/{self.team.route}"),
			"description": textwrap.shorten(text, DESCRIPTION_LENGTH, placeholder="…") if text else "",
			"image": get_url(self.team.logo) if self.team.logo else "",
		}
