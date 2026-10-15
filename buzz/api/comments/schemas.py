from datetime import datetime

from buzz.api.schemas import APIResponse


class CommentItem(APIResponse):
	name: str
	content: str
	owner: str
	owner_name: str
	owner_image: str | None
	creation: datetime
