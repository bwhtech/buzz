import frappe

from buzz.api.communities.schemas import CommunityRequest, EventOption
from buzz.www.events import TIME_FIELDS, exclude_ended_events, upcoming_filters

EVENT_OPTION_LIMIT = 20


def request_rows(**conditions) -> list[CommunityRequest]:
	"""Requests matching `conditions`, each with its event and both teams spelled out."""
	request, event, user = (
		frappe.qb.DocType(name) for name in ("Community Event Request", "Buzz Event", "User")
	)
	event_team, community = frappe.qb.DocType("Buzz Team").as_("event_team"), frappe.qb.DocType("Buzz Team")
	query = (
		frappe.qb.from_(request)
		.join(event)
		.on(event.name == request.event)
		.join(event_team)
		.on(event_team.name == request.event_team)
		.join(community)
		.on(community.name == request.community)
		.left_join(user)
		.on(user.name == request.submitted_by)
		.select(
			request.name,
			request.event,
			event.title.as_("event_title"),
			event.route.as_("event_route"),
			event.start_date,
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
		.orderby(event.start_date)
	)
	for field, value in conditions.items():
		query = query.where(request[field] == value)
	return [CommunityRequest(**row) for row in query.run(as_dict=True)]


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


def not_in_filter(values: list) -> list:
	# An empty `not in` list is invalid SQL; no row has an empty name.
	return ["not in", values or [""]]
