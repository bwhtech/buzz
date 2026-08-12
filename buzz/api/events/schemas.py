from datetime import date, timedelta

from buzz.api.schemas import APIResponse


class MyEvent(APIResponse):
	name: str
	title: str
	route: str | None = None
	start_date: date
	end_date: date | None = None
	start_time: timedelta | None = None
	end_time: timedelta | None = None
	venue: str | None = None
	medium: str | None = None
	banner_image: str | None = None
	is_published: bool
	is_host: bool
	team: str | None = None
	team_name: str | None = None
	team_logo: str | None = None


class MyEventsResponse(APIResponse):
	upcoming: list[MyEvent]
	past: list[MyEvent]
