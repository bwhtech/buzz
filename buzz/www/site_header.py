import frappe
from frappe.website.doctype.website_settings.website_settings import get_website_settings

from buzz.api.account import get_enabled_languages
from buzz.events.doctype.buzz_theme.buzz_theme import resolve_theme, theme_css

LANGUAGE_COOKIE = "preferred_language"
LANGUAGE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
DEFAULT_LOGO = "/assets/buzz/images/buzz-logo.svg"


def apply_site_context(context, preferred_theme: str | None = None):
	context.update(get_website_settings(context))
	context.update(SiteHeader().as_context())
	context.theme_css = page_theme_css(preferred_theme)


def page_theme_css(preferred_theme: str | None) -> str:
	default_theme = frappe.db.get_single_value("Buzz Settings", "event_page_theme")
	name = resolve_theme(preferred_theme, default_theme)
	return theme_css(name) if name else ""


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
