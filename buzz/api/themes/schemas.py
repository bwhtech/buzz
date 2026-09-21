from buzz.api.schemas import APIResponse


class ThemeOptions(APIResponse):
	can_edit: bool
	fonts: dict[str, str]
	preview_route: str | None = None
