from datetime import datetime
from typing import Literal

from pydantic import Field

from buzz.api.schemas import APIResponse


class ActivityEntry(APIResponse):
	name: str
	kind: Literal["comment", "email", "change", "created"]
	owner: str
	owner_name: str
	owner_image: str | None = None
	creation: datetime
	content: str | None = None
	recipients: list[str] = Field(default_factory=list)
	received: bool = False
	field: str | None = None
	old_value: str | None = None
	new_value: str | None = None
