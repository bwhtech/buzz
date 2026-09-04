from datetime import date, datetime, timedelta

from pydantic import Field

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


class EventProposalsResponse(APIResponse):
	"""One page of an event's talk proposals, with the counts the header reads."""

	title: str | None = None
	# Everyone who submitted, then everyone the current search and filters match.
	total: int
	matched: int
	proposals: list[ProposalListItem]
	has_next_page: bool = False
	# Whether this reader may change a proposal, so the drawer offers the control only to
	# someone the server will accept it from. Read access alone is a Viewer or Frontdesk.
	can_write: bool = False


class DailySubmissions(APIResponse):
	date: date
	count: int


class StatusTotal(APIResponse):
	status: str
	count: int


class ProposalTrend(APIResponse):
	"""How submissions have run, for the card above the proposal list."""

	total: int
	per_day: list[DailySubmissions]
	# All-time, like `total` — the window is a shape over time, a status is a share of a whole.
	by_status: list[StatusTotal] = Field(default_factory=list)
