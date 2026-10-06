import textwrap
from itertools import groupby

import frappe
from frappe import _
from frappe.utils import date_diff, format_date, get_url, getdate, today

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
EVENT_FIELDS = CARD_FIELDS + TIME_FIELDS


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
		}

	def upcoming_events(self) -> list:
		events = frappe.get_all(
			"Buzz Event",
			filters=upcoming_filters() | {"team": self.team.name},
			fields=EVENT_FIELDS,
			order_by="start_date asc, start_time asc",
			limit=LISTING_LIMIT,
		)
		return exclude_ended_events(events)

	def past_events(self) -> list:
		# By start date: a one-day event leaves end_date blank, and has_ended makes the exact cut.
		events = frappe.get_all(
			"Buzz Event",
			filters={
				"team": self.team.name,
				"is_published": 1,
				"route": ["is", "set"],
				"start_date": ["<=", today()],
			},
			fields=EVENT_FIELDS,
			order_by="start_date desc, start_time desc",
			limit=PAST_LIMIT,
		)
		return [event for event in events if has_ended(event)]

	def card(self, event) -> dict:
		is_online = event.medium == "Online"
		return {
			"date": str(getdate(event.start_date)),
			"title": event.title,
			"url": f"/events/{event.route}",
			"image": event.card_image or event.banner_image,
			"time": format_time(event.start_time),
			"host_name": self.team.team_name,
			"host_logo": self.team.logo,
			"place": _("Online") if is_online else event.venue_name,
			"is_online": is_online,
		}

	def meta(self) -> dict:
		text = self.team.short_description or plain_text(self.team.about)
		return {
			"url": get_url(f"/{self.team.route}"),
			"description": textwrap.shorten(text, DESCRIPTION_LENGTH, placeholder="…") if text else "",
			"image": get_url(self.team.logo) if self.team.logo else "",
		}
