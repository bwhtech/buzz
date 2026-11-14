from datetime import datetime
from typing import Literal

from pydantic import Field

from buzz.api.schemas import APIRequest, APIResponse


class AttachmentRequest(APIRequest):
	kind: Literal["invoice", "tickets", "ticket", "file"]
	ticket: str | None = None
	file: str | None = None


class EmailAttachment(APIResponse):
	name: str
	url: str
	size: int


class ActivityEntry(APIResponse):
	name: str
	kind: Literal["comment", "email", "change", "created", "edit"]
	owner: str
	owner_name: str
	owner_image: str | None = None
	creation: datetime
	content: str | None = None
	quoted_content: str | None = None
	snippet: str | None = None
	attachments: list[EmailAttachment] = Field(default_factory=list)
	recipients: list[str] = Field(default_factory=list)
	cc: list[str] = Field(default_factory=list)
	received: bool = False
	field: str | None = None
	fields: list[str] = Field(default_factory=list)
	old_value: str | None = None
	new_value: str | None = None
