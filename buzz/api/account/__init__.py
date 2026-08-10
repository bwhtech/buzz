import frappe
from frappe.translate import get_all_translations

from buzz.api.account.exceptions import UnknownLanguage
from buzz.api.account.schemas import GuestInfoResponse, LanguageOption, UserInfoResponse
from buzz.api.account.services import get_request_language


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_user_info() -> UserInfoResponse | GuestInfoResponse:
	if frappe.session.user == "Guest":
		return GuestInfoResponse(
			is_logged_in=False,
			brand_image=frappe.get_cached_value("Website Settings", "Website Settings", "banner_image"),
			language=get_request_language(),
		)

	user = frappe.get_cached_doc("User", frappe.session.user)

	return UserInfoResponse(
		name=user.name,
		is_logged_in=True,
		first_name=user.first_name,
		last_name=user.last_name,
		full_name=user.full_name,
		email=user.email,
		user_image=user.user_image,
		roles=user.roles,
		brand_image=frappe.get_single_value("Website Settings", "banner_image"),
		language=user.language,
	)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_enabled_languages() -> list[LanguageOption]:
	languages = frappe.get_all(
		"Language",
		filters={"enabled": 1},
		fields=["name", "language_name", "language_code"],
		order_by="language_name",
	)
	return [LanguageOption(**language) for language in languages]


# Deliberately not guest-whitelisted: every guest shares the one `Guest` User,
# so a write here would set the language for every other visitor. Guests switch
# language through the `preferred_language` cookie instead.
@frappe.whitelist(methods=["POST"])
def update_user_language(language_code: str) -> None:
	if not frappe.db.exists("Language", {"language_code": language_code}):
		UnknownLanguage.throw(language_code=language_code)

	frappe.db.set_value("User", frappe.session.user, "language", language_code)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_translations() -> dict:
	return get_all_translations(get_request_language())


def has_app_permission() -> bool:
	return True
