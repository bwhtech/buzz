from buzz.api.schemas import APIResponse


class ProviderLogin(APIResponse):
	name: str
	provider_name: str
	icon: str
	auth_url: str


class LoginContextResponse(APIResponse):
	disable_signup: int
	disable_user_pass_login: int
	login_with_email_link: int
	login_banner: str | None
	provider_logins: list[ProviderLogin]
