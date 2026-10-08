import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce
from frappe.utils import get_datetime

from buzz.api.communities.schemas import CommunityRequest, EventOption
from buzz.www.events import TIME_FIELDS, exclude_ended_events, upcoming_filters

EVENT_OPTION_LIMIT = 20


def request_rows(**conditions) -> list[CommunityRequest]:
	"""Requests matching `conditions`, each with its event and both teams spelled out.

	An external event has no Buzz Event or team: its row comes from the request's own fields.
	"""
	request, event, user, venue = (
		frappe.qb.DocType(name) for name in ("Community Event Request", "Buzz Event", "User", "Event Venue")
	)
	event_team, community = frappe.qb.DocType("Buzz Team").as_("event_team"), frappe.qb.DocType("Buzz Team")
	query = (
		frappe.qb.from_(request)
		.left_join(event)
		.on(event.name == request.event)
		.left_join(event_team)
		.on(event_team.name == request.event_team)
		.join(community)
		.on(community.name == request.community)
		.left_join(user)
		.on(user.name == request.submitted_by)
		.left_join(venue)
		.on(venue.name == event.venue)
		.select(
			request.name,
			request.event,
			request.event_title,
			request.is_external_event,
			request.event_url,
			request.host,
			request.event_location,
			request.start_datetime,
			event.route.as_("event_route"),
			event.start_date,
			event.start_time,
			event.medium,
			venue.venue_name,
			request.event_team,
			event_team.team_name.as_("event_team_name"),
			event_team.logo.as_("event_team_logo"),
			request.community,
			community.team_name.as_("community_name"),
			request.status,
			request.submitted_by,
			user.full_name.as_("submitter_name"),
			request.review_note,
		)
		.orderby(Coalesce(event.start_date, request.start_datetime))
	)
	for field, value in conditions.items():
		query = query.where(request[field] == value)
	return [CommunityRequest(**request_row(row)) for row in query.run(as_dict=True)]


def request_row(row) -> dict:
	"""Fills an external event's date, time, place and host from the request itself."""
	medium, venue = row.pop("medium"), row.pop("venue_name")
	starts_at, location, host = row.pop("start_datetime"), row.pop("event_location"), row.pop("host")
	row.place = _("Online") if medium == "Online" else venue
	if row.is_external_event:
		starts_at = get_datetime(starts_at)
		start = starts_at - starts_at.replace(hour=0, minute=0, second=0, microsecond=0)
		row.update(start_date=starts_at.date(), start_time=start, place=location, event_team_name=host)
	return row


def upcoming_event_options(filters: dict) -> list[EventOption]:
	"""Published events that have not ended, as picker options."""
	events = frappe.get_all(
		"Buzz Event",
		filters=upcoming_filters() | filters,
		fields=["name", "title", "start_date", "team.team_name as team_name", *TIME_FIELDS],
		order_by="start_date asc",
		limit=EVENT_OPTION_LIMIT,
	)
	return [
		EventOption(
			name=str(event.name), title=event.title, start_date=event.start_date, team_name=event.team_name
		)
		for event in exclude_ended_events(events)
	]
