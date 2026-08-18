import os
import re

import frappe
from frappe.utils.html_utils import unescape_html

from buzz.buzz_themes.doctype.buzz_theme.buzz_theme import get_render_theme_context, is_within_directory


def buzz_theme_asset_url(path):
	context = get_render_theme_context()
	if not context["theme_name"]:
		return ""

	relative_path = path.lstrip("/")
	apps = context["apps"]

	for name in context["names"]:
		app = apps[name]
		slug = frappe.scrub(name)
		theme_public_dir = os.path.join(frappe.get_app_path(app), "public", "themes", slug)
		asset_path = os.path.join(theme_public_dir, relative_path)
		if is_within_directory(theme_public_dir, asset_path) and os.path.isfile(asset_path):
			return f"/assets/{app}/themes/{slug}/{relative_path}"

	active_name = context["names"][0]
	active_app = apps[active_name]
	active_slug = frappe.scrub(active_name)
	return f"/assets/{active_app}/themes/{active_slug}/{relative_path}"


def buzz_theme_config():
	context = get_render_theme_context()
	settings_doctype = context.get("settings_doctype")
	if not settings_doctype:
		return frappe._dict()

	return frappe.get_cached_doc(settings_doctype)


# Venue.google_maps_embed_code is a Code field, and Frappe deliberately skips XSS sanitization
# for Code fieldtypes, so the pasted value is attacker-controlled markup for anyone holding the
# Event Manager role. Never render the paste: pull the src out, prove it is a Google Maps embed,
# and let the theme build its own iframe around the URL.
GOOGLE_MAPS_EMBED_PREFIXES = (
	"https://www.google.com/maps/embed",
	"https://maps.google.com/maps",
)
IFRAME_SRC_PATTERN = re.compile(r"""\bsrc\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def buzz_map_embed_url(embed_code):
	if not embed_code:
		return ""

	candidate = embed_code.strip()
	if "<" in candidate:
		match = IFRAME_SRC_PATTERN.search(candidate)
		if not match:
			return ""
		candidate = match.group(1).strip()

	candidate = unescape_html(candidate)
	if not candidate.startswith(GOOGLE_MAPS_EMBED_PREFIXES):
		return ""

	return candidate
