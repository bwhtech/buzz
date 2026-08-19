from buzz.api.schemas import APIResponse


class TeamOption(APIResponse):
	name: str
	team_name: str
	logo: str | None
	team_role: str


class TeamMember(APIResponse):
	user: str
	full_name: str | None
	user_image: str | None
	team_role: str


class TeamOverview(APIResponse):
	name: str
	team_name: str
	slug: str | None
	logo: str | None
	my_role: str
	members: list[TeamMember]
