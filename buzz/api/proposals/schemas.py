from datetime import datetime

from buzz.api.schemas import APIResponse


class ProposalListItem(APIResponse):
	name: str
	title: str
	event: str
	event_title: str | None = None
	status: str
	creation: datetime
