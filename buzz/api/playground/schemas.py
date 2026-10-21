from buzz.api.schemas import APIResponse


class RedirectResponse(APIResponse):
	redirect_to: str


class ChecklistStep(APIResponse):
	name: str
	title: str
	description: str
	persona: str
	path: str
	completed: bool
	optional: bool
	locked: bool
	completes_on: str | None
	target: str | None


class ChecklistGroup(APIResponse):
	name: str
	title: str
	steps: list[ChecklistStep]


class InboxAttachment(APIResponse):
	name: str
	file_name: str


class InboxEmail(APIResponse):
	name: str
	subject: str | None
	sender: str | None
	recipient: str | None
	creation: str
	message: str | None
	attachments: list[InboxAttachment]
