from buzz.api.schemas import APIResponse


class CommunityDraft(APIResponse):
	name: str
	team_name: str
	slug: str | None
	logo: str | None
	short_description: str | None


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
