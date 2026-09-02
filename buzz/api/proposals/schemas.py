from datetime import date, datetime, timedelta

from buzz.api.schemas import APIResponse


class ProposalSpeakerItem(APIResponse):
	first_name: str
	last_name: str | None = None
	email: str


class ProposalListItem(APIResponse):
	name: str
	title: str
	event: str
	# Joined over the event link, so a deleted event leaves them empty.
	event_title: str | None = None
	start_date: date | None = None
	start_time: timedelta | None = None
	end_date: date | None = None
	venue: str | None = None
	banner_image: str | None = None
	allow_editing_talks_after_acceptance: bool = False
	status: str
	creation: datetime
	modified: datetime
	speakers: list[ProposalSpeakerItem]
