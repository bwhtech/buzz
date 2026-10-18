from datetime import datetime

from buzz.api.filters.schemas import FilterField
from buzz.api.schemas import APIResponse


class RecipientCount(APIResponse):
	count: int


class CommunicationItem(APIResponse):
	name: str
	audience: str
	# JSON `[field, operator, value]` triples, as the dashboard lists send them.
	filters: str
	subject: str
	message: str
	recipient_count: int
	scheduled_at: datetime | None
	sent_by: str
	creation: datetime


class EventCommunicationsResponse(APIResponse):
	title: str | None
	can_write: bool
	# Owner/Admin only: the support email belongs to the team, not the event.
	can_edit_settings: bool
	support_email: str | None
	filter_fields: dict[str, list[FilterField]]
	communications: list[CommunicationItem]
