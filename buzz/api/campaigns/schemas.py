from buzz.api.schemas import APIResponse


class CampaignResponse(APIResponse):
	title: str
	description: str | None
	event: str | None
