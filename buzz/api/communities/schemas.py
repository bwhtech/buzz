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
	event: str
	event_title: str
	event_route: str | None
	start_date: date
	start_time: timedelta | None
	# The venue, or "Online".
	place: str | None
	event_team: str
	event_team_name: str
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
