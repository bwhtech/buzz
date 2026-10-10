from buzz.api.schemas import APIResponse


class TagItem(APIResponse):
	name: str
	label: str
