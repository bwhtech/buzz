from buzz.api.schemas import APIResponse


class TeamOption(APIResponse):
	name: str
	team_name: str
	logo: str | None
	team_role: str
