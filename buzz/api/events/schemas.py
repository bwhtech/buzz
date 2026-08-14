from datetime import date, timedelta

from pydantic import Field

from buzz.api.schemas import APIRequest, APIResponse


class MyEvent(APIResponse):
	name: str
	title: str
	route: str | None = None
	start_date: date
	end_date: date | None = None
	start_time: timedelta | None = None
	venue: str | None = None
	banner_image: str | None = None
	is_host: bool
	team: str | None = None
	team_name: str | None = None
	team_logo: str | None = None


class MyEventsResponse(APIResponse):
	upcoming: list[MyEvent]
	past: list[MyEvent]


class EventVenue(APIResponse):
	name: str
	address: str | None = None


class EventDetail(APIResponse):
	"""One event, with everything the manage page edits or shows."""

	name: str
	title: str
	route: str | None = None
	team: str | None = None
	start_date: date
	end_date: date | None = None
	start_time: timedelta | None = None
	end_time: timedelta | None = None
	time_zone: str | None = None
	short_description: str | None = None
	about: str | None = None
	banner_image: str | None = None
	medium: str | None = None
	venue: EventVenue | None = None
	# The organiser's own link, or the one Zoom issued when the meeting was booked.
	meeting_link: str | None = None
	is_published: bool


class GuestAddOn(APIResponse):
	title: str
	# The option the attendee picked, for an add-on that offers a choice.
	value: str | None = None


class EventGuest(APIResponse):
	"""One ticket. A person who booked twice holds two, and appears twice."""

	name: str
	attendee_name: str | None = None
	attendee_email: str | None = None
	ticket_type: str | None = None
	add_ons: list[GuestAddOn] = Field(default_factory=list)


class EventGuestsResponse(APIResponse):
	total: int
	guests: list[EventGuest]


class RouteAvailability(APIResponse):
	available: bool
	message: str


class NewEvent(APIRequest):
	team: str
	title: str
	start_date: date
	start_time: timedelta
	end_time: timedelta
	end_date: date | None = None
	about: str | None = None
	banner_image: str | None = None
	time_zone: str | None = None
	venue: str | None = None
	# Zoom cannot be booked before the event exists, so the dashboard asks for it here
	# and the service books it once the event is saved.
	zoom_meeting: bool = False


class CreatedEvent(APIResponse):
	name: str
	title: str
