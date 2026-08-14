from datetime import date, timedelta

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
