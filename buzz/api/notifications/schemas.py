from datetime import datetime
from typing import Literal

from buzz.api.schemas import APIResponse


class NotificationEntry(APIResponse):
	name: str
	kind: Literal["comment", "reply"]
	actor: str
	actor_image: str | None = None
	snippet: str | None = None
	creation: datetime
	read: bool


class NotificationGroup(APIResponse):
	reference_doctype: str
	reference_name: str
	title: str | None = None
	event_title: str | None = None
	link: str | None = None
	subscribed: bool
	notifications: list[NotificationEntry]
