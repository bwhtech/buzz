from datetime import date, timedelta
from typing import Literal

from buzz.api.schemas import APIRequest, APIResponse


class CommunityDraft(APIResponse):
	name: str
	team_name: str
	slug: str | None
	logo: str | None
	short_description: str | None


class EventDraft(APIResponse):
	name: str
	team: str
	title: str
	start_date: date
	start_time: str
	medium: str
	venue_name: str | None


class InvitedTeam(APIResponse):
	name: str
	team_name: str
	logo: str | None
	team_role: str
	invited_by: str | None
	member_count: int
	upcoming_event_count: int


class OnboardingState(APIResponse):
	personal_teams_enabled: bool
	communities_enabled: bool
	invited_team: InvitedTeam | None
	community: CommunityDraft | None
	draft_event: EventDraft | None


class FirstEvent(APIRequest):
	team: str
	title: str
	start_date: date
	start_time: timedelta
	medium: Literal["Online", "In Person"]
	venue_name: str | None = None
	# The draft saved on an earlier pass, so going back and forth edits it instead of adding more.
	event: str | None = None


class SavedRecord(APIResponse):
	name: str
