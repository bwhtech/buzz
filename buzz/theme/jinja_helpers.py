import os

import frappe

from buzz.theme.doctype.buzz_theme.buzz_theme import get_render_theme_context
from buzz.theme.theme_resolver import is_within_directory


def theme_asset_url(path):
	"""Resolve a static asset URL for the active theme.

	Walks the theme inheritance chain so a child theme can override an asset
	by shipping a file at the same relative path. Each theme's files may live
	in a different content app (resolved via its `module`), so both the
	filesystem lookup and the `/assets/<app>/...` URL are app-aware. Falls
	back to the base theme's URL if no file is found (so themes can document
	expected paths without forcing every child to ship every asset)."""
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

	base_name = context["names"][0]
	base_app = apps[base_name]
	base_slug = frappe.scrub(base_name)
	return f"/assets/{base_app}/themes/{base_slug}/{relative_path}"


def theme_config():
	"""Return the active theme's settings doc (from the linked Single DocType).

	The theme owner creates a `<Theme Name> Settings` Single DocType via the
	'Scaffold Theme Settings' button on the Buzz Theme form, then adds
	whatever fields the theme needs. Returns an empty dict if no settings
	DocType is linked."""
	context = get_render_theme_context()
	settings_doctype = context.get("settings_doctype")
	if not settings_doctype:
		return frappe._dict()

	return frappe.get_cached_doc(settings_doctype)
