from buzz.api.schemas import APIResponse


class NavbarLink(APIResponse):
	label: str
	url: str | None
	open_in_new_tab: bool
	right: bool
	child_items: list["NavbarLink"]


class Navbar(APIResponse):
	links: list[NavbarLink]
	call_to_action: str | None
	call_to_action_url: str | None
	show_login: bool
	show_search: bool
	show_language_picker: bool


class GuestInfoResponse(APIResponse):
	is_logged_in: bool
	brand_image: str | None
	navbar: Navbar
	# Resolved per browser, so the switcher can show a guest the language in effect.
	language: str


class UserInfoResponse(APIResponse):
	name: str
	is_logged_in: bool
	first_name: str | None
	last_name: str | None
	full_name: str | None
	email: str
	user_image: str | None
	bio: str | None
	# Rows of the User.roles child table, serialized as full documents.
	roles: list
	brand_image: str | None
	navbar: Navbar
	language: str | None
	time_zone: str | None


class LanguageOption(APIResponse):
	name: str
	language_name: str
	language_code: str
