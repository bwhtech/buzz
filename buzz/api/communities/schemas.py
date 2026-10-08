from datetime import date, timedelta

from buzz.api.schemas import APIResponse


class CommunityOption(APIResponse):
	name: str
	team_name: str
	logo: str | None


class EventOption(APIResponse):
	name: str
	title: str
	start_date: date
	team_name: str


class CommunityRequest(APIResponse):
	name: str
	# Unset for an external event, which lives on another platform at `event_url`.
	event: str | None
	is_external_event: bool
	event_url: str | None
	event_title: str
	event_route: str | None
	start_date: date
	start_time: timedelta | None
	# The venue, "Online", or for an external event its location.
	place: str | None
	event_team: str | None
	# The event's team, or for an external event its host.
	event_team_name: str | None
	event_team_logo: str | None
	community: str
	community_name: str
	status: str
	submitted_by: str | None
	submitter_name: str | None
	review_note: str | None


class EventRequests(APIResponse):
	requests: list[CommunityRequest]
	# Published communities this event has no request with yet.
	communities: list[CommunityOption]


class CommunityQueue(APIResponse):
	pending: list[CommunityRequest]
	approved: list[CommunityRequest]
