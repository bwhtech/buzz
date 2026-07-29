from buzz.api.schemas import APIResponse


class GuestInfoResponse(APIResponse):
	is_logged_in: bool
	brand_image: str | None


class UserInfoResponse(APIResponse):
	name: str
	is_logged_in: bool
	first_name: str | None
	last_name: str | None
	full_name: str | None
	email: str
	user_image: str | None
	# Rows of the User.roles child table, serialized as full documents.
	roles: list
	brand_image: str | None
	language: str | None


class LanguageOption(APIResponse):
	name: str
	language_name: str
	language_code: str
