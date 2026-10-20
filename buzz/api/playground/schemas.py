from buzz.api.schemas import APIResponse


class RedirectResponse(APIResponse):
	redirect_to: str


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
