from buzz.api.schemas import APIResponse


class PaletteEvent(APIResponse):
	name: str
	title: str
	team_title: str | None = None
	access: dict[str, str | None]


class PaletteEventsResponse(APIResponse):
	events: list[PaletteEvent]


class SearchRecord(APIResponse):
	name: str
	title: str
	subtitle: str | None = None


class SearchGroup(APIResponse):
	key: str
	records: list[SearchRecord]


class EventSearchResponse(APIResponse):
	groups: list[SearchGroup]
