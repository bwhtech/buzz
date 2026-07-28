import frappe
from frappe import _
from frappe.translate import get_all_translations

from buzz.api.account.schemas import GuestInfoResponse, LanguageOption, UserInfoResponse
from buzz.api.exceptions import BuzzAPIError


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_user_info() -> UserInfoResponse | GuestInfoResponse:
	if frappe.session.user == "Guest":
		return GuestInfoResponse(
			is_logged_in=False,
			brand_image=frappe.get_cached_value("Website Settings", "Website Settings", "banner_image"),
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


@frappe.whitelist()
def update_user_language(language_code: str) -> None:
	if not frappe.db.exists("Language", {"language_code": language_code}):
		frappe.throw(_("Invalid language"), BuzzAPIError)

	frappe.db.set_value("User", frappe.session.user, "language", language_code)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_translations() -> dict:
	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("System Settings", "language")

	return get_all_translations(language)


def has_app_permission() -> bool:
	return True
