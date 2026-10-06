import textwrap
from itertools import groupby

import frappe
from frappe import _
from frappe.utils import date_diff, flt, format_date, get_url, getdate, today

from buzz.events.doctype.buzz_team.team_map import TeamMap
from buzz.www.event.date_range import format_time
from buzz.www.event.index import public_links
from buzz.www.event.meta import DESCRIPTION_LENGTH, plain_text
from buzz.www.events import (
	CARD_FIELDS,
	LISTING_LIMIT,
	TIME_FIELDS,
	exclude_ended_events,
	has_ended,
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
EVENT_FIELDS = CARD_FIELDS + TIME_FIELDS + VENUE_FIELDS + HOST_FIELDS


def day_labels(day) -> dict:
	relative = {0: _("Today"), 1: _("Tomorrow")}.get(date_diff(day, today()))
	return {"label": relative or format_date(day, "d MMM"), "weekday": format_date(day, "EEEE")}


def group_by_day(cards: list[dict]) -> list[dict]:
	return [
		{"date": date, **day_labels(getdate(date)), "events": list(group)}
		for date, group in groupby(cards, key=lambda card: card["date"])
	]


class TeamPage:
	"""Context for a team's public page: identity, links and its own event timeline."""

	def __init__(self, team):
		self.team = team

	def as_context(self) -> dict:
		upcoming = [self.card(event) for event in self.upcoming_events()]
		past = [self.card(event) for event in self.past_events()]
		return {
			"title": self.team.team_name,
			"links": public_links(self.team.links),
			"events_hosted": frappe.db.count("Buzz Event", {"team": self.team.name, "is_published": 1}),
			"upcoming_days": group_by_day(upcoming),
			"past_days": group_by_day(past),
			"meta": self.meta(),
			**TeamMap(upcoming, past).as_context(),
		}

	def upcoming_events(self) -> list:
		events = frappe.get_all(
			"Buzz Event",
			filters=upcoming_filters(),
			or_filters=self.event_filters(),
			fields=EVENT_FIELDS,
			order_by="start_date asc, start_time asc",
			limit=LISTING_LIMIT,
		)
		return exclude_ended_events(events)

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
		return [event for event in events if has_ended(event)]

	def event_filters(self) -> dict:
		"""The team's own events, plus those its community approved."""
		filters = {"team": self.team.name}
		if self.team.is_a_community:
			approved = {"community": self.team.name, "status": "Approved"}
			filters["name"] = [
				"in",
				frappe.get_all("Community Event Request", filters=approved, pluck="event"),
			]
		return filters

	def card(self, event) -> dict:
		is_online = event.medium == "Online"
		has_location = not is_online and bool(flt(event.latitude) and flt(event.longitude))
		return {
			"route": event.route,
			"date": str(getdate(event.start_date)),
			"title": event.title,
			"url": f"/events/{event.route}",
			"image": event.card_image or event.banner_image,
			"time": format_time(event.start_time),
			"host_name": event.host_name,
			"host_logo": event.host_logo,
			"place": _("Online") if is_online else event.venue_name,
			"is_online": is_online,
			"city": event.city,
			"country": event.country,
			"latitude": flt(event.latitude) if has_location else None,
			"longitude": flt(event.longitude) if has_location else None,
		}

	def meta(self) -> dict:
		text = self.team.short_description or plain_text(self.team.about)
		return {
			"url": get_url(f"/{self.team.route}"),
			"description": textwrap.shorten(text, DESCRIPTION_LENGTH, placeholder="…") if text else "",
			"image": get_url(self.team.logo) if self.team.logo else "",
		}
