import frappe
from frappe.utils import md_to_html
from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth_keys

from buzz.api.auth.schemas import LoginContextResponse, ProviderLogin


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_login_context(redirect_to: str | None = None) -> LoginContextResponse:
	raw_banner = frappe.db.get_single_value("Buzz Settings", "login_banner")

	return LoginContextResponse(
		disable_signup=frappe.get_website_settings("disable_signup"),
		disable_user_pass_login=frappe.get_system_settings("disable_user_pass_login"),
		login_with_email_link=frappe.get_system_settings("login_with_email_link"),
		login_banner=md_to_html(raw_banner) if raw_banner else None,
		provider_logins=get_provider_logins(redirect_to or frappe.utils.get_url("/b")),
	)


def get_provider_logins(redirect_to: str) -> list[ProviderLogin]:
	social_login_keys = frappe.get_all(
		"Social Login Key",
		filters={"enable_social_login": 1},
		fields=["name", "provider_name", "icon", "client_id", "base_url"],
	)

	return [
		ProviderLogin(
			name=provider.name,
			provider_name=provider.provider_name,
			icon=provider.icon or "",
			auth_url=get_oauth2_authorize_url(provider.name, redirect_to),
		)
		for provider in social_login_keys
		if provider.client_id and provider.base_url and get_oauth_keys(provider.name)
	]
