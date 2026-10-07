import frappe
from frappe.utils.user import get_fullname_and_avatar
from frappe.website.doctype.website_settings.website_settings import get_website_settings

from buzz.events.doctype.buzz_theme.buzz_theme import resolve_theme, theme_css

DEFAULT_LOGO = "/assets/buzz/images/buzz-logo-no-bg.svg"
DEFAULT_FAVICON = "/assets/buzz/dashboard/favicon.png"


def apply_site_context(context, preferred_theme: str | None = None):
	context.update(get_website_settings(context))
	context.update(SiteHeader().as_context())
	# Event pages skip frappe-web.bundle.js, which other apps' web scripts expect
	context.update(body_class="event-page", web_include_js=["website_script.js"], web_include_icons=[])
	theme = resolve_theme(preferred_theme, frappe.db.get_single_value("Buzz Settings", "event_page_theme"))
	context.theme_css = theme_css(theme) if theme else ""
	context.default_mode = frappe.db.get_value("Buzz Theme", theme, "color_scheme") if theme else "dark"


class SiteHeader:
	def __init__(self):
		self.is_guest = frappe.session.user == "Guest"
		self.settings = frappe.get_cached_doc("Website Settings")

	def as_context(self) -> dict:
		return {
			"brand": self.brand(),
			"favicon": self.settings.favicon or DEFAULT_FAVICON,
			"is_guest": self.is_guest,
			**self.user_info(),
		}

	def user_info(self) -> dict:
		# www pages get these from TemplatePage; a website generator's DocumentPage does not.
		info = get_fullname_and_avatar(frappe.session.user)
		return {"user": info.name, "fullname": info.fullname, "user_image": info.avatar}

	def brand(self) -> dict:
		# Same logo the dashboard's navbar shows (brand_image in get_user_info)
		logo = self.settings.banner_image or self.settings.app_logo or DEFAULT_LOGO
		return {"logo": logo, "name": self.settings.app_name or "Buzz", "is_default": logo == DEFAULT_LOGO}
