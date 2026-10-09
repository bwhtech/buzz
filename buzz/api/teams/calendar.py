from datetime import timedelta

import frappe
from frappe.query_builder import Case
from frappe.utils import get_datetime

from buzz.api.communities.queries import time_of_day
from buzz.api.events.services import split_by_date
from buzz.api.teams.schemas import TeamEvent, TeamEvents
from buzz.permissions import has_team_access

REQUEST = "Community Event Request"


def team_events(team: str) -> TeamEvents:
	"""A team's own events, plus the Buzz and external events its community approved."""
	events = sorted(
		buzz_events(team) + external_events(team),
		key=lambda event: (event.start_date, event.start_time or timedelta(0)),
	)
	upcoming, past = split_by_date(events)
	return TeamEvents(upcoming=upcoming, past=past)


def buzz_events(team: str) -> list[TeamEvent]:
	event, request = frappe.qb.DocType("Buzz Event"), frappe.qb.DocType(REQUEST)
	host, venue = frappe.qb.DocType("Buzz Team"), frappe.qb.DocType("Event Venue")
	own = event.team == team
	approved = event.name.isin(
		frappe.qb.from_(request)
		.select(request.event)
		.where((request.community == team) & (request.status == "Approved"))
	)
	published = event.is_published == 1
	# Members also see their team's drafts; anyone else, published events only.
	visible = own if has_team_access(team, "read", frappe.session.user) else own & published
	rows = (
		frappe.qb.from_(event)
		.left_join(host)
		.on(host.name == event.team)
		.left_join(venue)
		.on(venue.name == event.venue)
		.select(
			event.name,
			event.title,
			event.route,
			event.start_date,
			event.end_date,
			event.start_time,
			event.end_time,
			venue.venue_name.as_("venue"),
			event.medium,
			event.banner_image,
			event.team,
			host.team_name,
			host.logo.as_("team_logo"),
			Case().when(own, 1).else_(0).as_("is_host"),
			Case().when(own, 0).else_(1).as_("is_community_request"),
		)
		.where(visible | (approved & published))
	).run(as_dict=True)
	# Buzz Event autonames to integers, while every link to it travels as a string.
	return [TeamEvent(**row | {"name": str(row.name), "is_attendee": False}) for row in rows]


def external_events(team: str) -> list[TeamEvent]:
	rows = frappe.get_all(
		REQUEST,
		filters={"community": team, "status": "Approved", "is_external_event": 1},
		fields=[
			"name",
			"event_title",
			"event_url",
			"host",
			"event_location",
			"start_datetime",
			"end_datetime",
		],
	)
	return [external_event(row) for row in rows]


def external_event(row) -> TeamEvent:
	starts_at, ends_at = get_datetime(row.start_datetime), get_datetime(row.end_datetime)
	return TeamEvent(
		name=row.name,
		title=row.event_title,
		start_date=starts_at.date(),
		end_date=ends_at.date(),
		start_time=time_of_day(starts_at),
		end_time=time_of_day(ends_at),
		venue=row.event_location,
		team_name=row.host,
		event_url=row.event_url,
		is_host=False,
		is_attendee=False,
		is_community_request=True,
		is_external=True,
	)
