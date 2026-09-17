from datetime import date, datetime

from buzz.api.schemas import APIResponse


class EnquiryFormState(APIResponse):
	name: str
	closed: bool
	link: str | None


class TierItem(APIResponse):
	name: str
	title: str
	price: float
	currency: str | None
	enabled: bool
	perks: str | None
	sponsor_count: int


class EventSponsorItem(APIResponse):
	name: str
	company_name: str
	company_logo: str | None
	website: str | None
	country: str | None
	contact_email: str | None
	enquiry: str | None
	tier: str | None
	tier_title: str


class EventEnquiryItem(APIResponse):
	name: str
	company_name: str
	company_logo: str | None
	website: str | None
	status: str
	tier: str | None
	tier_title: str
	tier_price: float | None
	tier_currency: str | None
	creation: datetime


class EventSponsorshipsResponse(APIResponse):
	title: str
	can_write: bool
	form: EnquiryFormState | None
	tiers: list[TierItem]
	sponsors: list[EventSponsorItem]


class EventEnquiriesResponse(APIResponse):
	"""One page of an event's enquiries, with the counts the section header reads."""

	total: int
	matched: int
	enquiries: list[EventEnquiryItem]
	has_next_page: bool = False


class EnquiryAnswer(APIResponse):
	label: str
	value: str | None
	fieldtype: str | None


class EnquiryDetail(APIResponse):
	"""Everything an organiser reads about one enquiry, answers included."""

	name: str
	company_name: str
	company_logo: str | None
	status: str
	tier: str | None
	tier_title: str
	website: str | None
	country: str | None
	phone: str | None
	contact: str | None
	creation: datetime
	modified: datetime
	sponsor: str | None
	answers: list[EnquiryAnswer]


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
