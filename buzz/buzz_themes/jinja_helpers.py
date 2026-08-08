import os

import frappe

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
