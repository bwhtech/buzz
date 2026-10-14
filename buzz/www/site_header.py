import frappe
from frappe import _
from frappe.utils.user import get_fullname_and_avatar
from frappe.website.doctype.website_settings.website_settings import (
	get_website_settings,
	modify_header_footer_items,
)

from buzz.events.doctype.buzz_theme.buzz_theme import resolve_theme, theme_css

BUZZ_NAVBAR = "Buzz Navbar"
DEFAULT_LOGO = "/assets/buzz/images/buzz-logo-no-bg.svg"
DEFAULT_FAVICON = "/assets/buzz/dashboard/favicon.png"


def apply_site_context(context, preferred_theme: str | None = None):
	context.update(get_website_settings(context))
	context.update(SiteHeader().as_context())
	# Event pages skip frappe-web.bundle.js, which other apps' web scripts expect
	context.update(body_class="event-page", web_include_js=["website_script.js"], web_include_icons=[])
	# Frappe's own navbar needs its website CSS and JS, which these pages otherwise skip
	context.native_navbar = context.get("navbar_template") != BUZZ_NAVBAR
	theme = resolve_theme(preferred_theme, frappe.db.get_single_value("Buzz Settings", "event_page_theme"))
	context.theme_css = theme_css(theme) if theme else ""
	context.default_mode = frappe.db.get_value("Buzz Theme", theme, "color_scheme") if theme else "dark"


def buzz_navbar() -> dict:
	"""Context for the Buzz Navbar web template, which any website page may render."""
	header = SiteHeader()
	navbar = header.navbar()
	languages = header.languages() if navbar["show_language_picker"] else []
	return {**header.as_context(), "navbar": navbar, "languages": languages, "language": frappe.local.lang}


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
		buzz_settings = frappe.get_cached_doc("Buzz Settings")
		return {
			"logo": buzz_settings.app_logo or DEFAULT_LOGO,
			"logo_dark": buzz_settings.app_logo_dark,
			"name": self.settings.app_name or "Buzz",
			"is_default": not buzz_settings.app_logo,
		}

	def navbar(self) -> dict:
		items = modify_header_footer_items(self.settings.top_bar_items)
		return {
			"links": [self.link(item) for item in items if not item.parent_label],
			"call_to_action": self.settings.call_to_action,
			"call_to_action_url": self.settings.call_to_action_url,
			"show_login": not self.settings.hide_login,
			"show_language_picker": bool(self.settings.show_language_picker),
		}

	def link(self, item) -> dict:
		return {
			"label": _(item.label),
			"url": item.url,
			"open_in_new_tab": bool(item.open_in_new_tab),
			"right": bool(item.right),
			"child_items": [self.link(child) for child in item.child_items if child.url],
		}

	def languages(self) -> list[dict]:
		return frappe.get_all(
			"Language",
			filters={"enabled": 1},
			fields=["language_name", "language_code"],
			order_by="language_name",
		)
