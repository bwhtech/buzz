import frappe

from buzz.api.account import get_enabled_languages

LANGUAGE_COOKIE = "preferred_language"
LANGUAGE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
DEFAULT_LOGO = "/assets/buzz/images/buzz-logo.svg"


class SiteHeader:
	def __init__(self):
		self.is_guest = frappe.session.user == "Guest"
		self.languages = get_enabled_languages()

	def as_context(self) -> dict:
		self.remember_guest_language()
		return {
			"brand": self.brand(),
			"is_guest": self.is_guest,
			"languages": self.languages,
			"current_language": frappe.local.lang,
		}

	def brand(self) -> dict:
		settings = frappe.get_cached_doc("Website Settings")
		return {"logo": settings.app_logo or DEFAULT_LOGO, "name": settings.app_name or "Buzz"}

	def remember_guest_language(self):
		# Guests share one User record, so their choice lives in a cookie, as in the dashboard
		code = frappe.form_dict.get("_lang")
		if not self.is_guest or code not in {language.language_code for language in self.languages}:
			return
		frappe.local.cookie_manager.set_cookie(LANGUAGE_COOKIE, code, max_age=LANGUAGE_COOKIE_MAX_AGE)
