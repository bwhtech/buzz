from datetime import date

from buzz.api.schemas import APIResponse


class PaletteEvent(APIResponse):
	name: str
	title: str
	team: str | None = None
	team_title: str | None = None
	start_date: date | None = None
	end_date: date | None = None
	access: dict[str, str | None]


class PaletteEventsResponse(APIResponse):
	events: list[PaletteEvent]


class SearchRecord(APIResponse):
	name: str
	title: str
	subtitle: str | None = None


class SearchGroup(APIResponse):
	key: str
	section: str
	records: list[SearchRecord]


class EventSearchResponse(APIResponse):
	groups: list[SearchGroup]
