from datetime import date, datetime

from buzz.api.schemas import APIResponse


class ProposalSpeakerItem(APIResponse):
	first_name: str
	last_name: str | None = None
	email: str


class ProposalListItem(APIResponse):
	name: str
	title: str
	event: str
	# Joined over the event link, so a deleted event leaves both empty.
	event_title: str | None = None
	start_date: date | None = None
	banner_image: str | None = None
	status: str
	creation: datetime
	modified: datetime
	speakers: list[ProposalSpeakerItem]
