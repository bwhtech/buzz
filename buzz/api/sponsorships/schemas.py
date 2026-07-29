from datetime import date, datetime

from buzz.api.schemas import APIResponse


class EnquirySummary(APIResponse):
	name: str
	company_name: str
	company_logo: str | None
	event: str
	tier: str | None
	tier_title: str
	status: str
	creation: datetime
	owner: str


class EventSummary(APIResponse):
	title: str
	short_description: str | None
	about: str | None
	start_date: date
	end_date: date | None
	venue: str | None
	route: str | None


class SponsorSummary(APIResponse):
	name: str
	company_name: str
	company_logo: str | None
	creation: datetime
	event: str
	tier: str
	tier_title: str


class SponsorshipDetailsResponse(APIResponse):
	enquiry: EnquirySummary
	event_details: EventSummary
	sponsor_details: SponsorSummary | None
	has_sponsor: bool


class SponsorshipListItem(APIResponse):
	name: str
	company_name: str
	event: str
	tier: str | None
	status: str
	creation: datetime
	event_title: str | None
	tier_title: str
	has_sponsor: bool
