import frappe
from frappe.website.doctype.website_settings.website_settings import get_website_settings

from buzz.events.doctype.buzz_theme.buzz_theme import resolve_theme, theme_css

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

	def as_context(self) -> dict:
		return {
			"brand": self.brand(),
			"is_guest": self.is_guest,
			"current_language": frappe.local.lang,
		}

	def brand(self) -> dict:
		# Same logo the dashboard's navbar shows (brand_image in get_user_info)
		settings = frappe.get_cached_doc("Website Settings")
		logo = settings.banner_image or settings.app_logo or DEFAULT_LOGO
		return {"logo": logo, "name": settings.app_name or "Buzz"}
