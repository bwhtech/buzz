from buzz.api.schemas import APIResponse


class TeamMember(APIResponse):
	user: str
	full_name: str | None
	user_image: str | None
	team_role: str


class TeamOption(APIResponse):
	name: str
	team_name: str
	logo: str | None
	team_role: str
	# The settings list shows who is on each team, not only how many.
	members: list[TeamMember]


class InviteOutcome(APIResponse):
	email: str
	status: str
	# Only someone who already has a User has a name to show; a stranger is still an address.
	full_name: str | None = None


class TeamInvite(APIResponse):
	email: str
	team_role: str


class TeamOverview(APIResponse):
	name: str
	team_name: str
	slug: str | None
	logo: str | None
	my_role: str
	members: list[TeamMember]
	# Kept apart from members: these people cannot do anything on the team yet.
	invites: list[TeamInvite]
