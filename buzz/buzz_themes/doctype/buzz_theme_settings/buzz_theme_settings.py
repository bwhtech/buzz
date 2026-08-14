import re

import frappe
from frappe.model.document import Document

# The routes every bundled theme ships pages for. Seeded from after_install AND from
# buzz.patches.seed_buzz_theme_routes: frappe logs patches as applied without running them
# on a fresh install, so a patch alone leaves new sites with no themed routes at all.
DEFAULT_ROUTES = [
	{"url_pattern": "^$", "template_path": "pages/home.html", "requires_auth": 0},
	{"url_pattern": "^home$", "template_path": "pages/home.html", "requires_auth": 0},
	{
		"url_pattern": "^events/(?P<event_route>[^/]+)$",
		"template_path": "pages/events/detail.html",
		"requires_auth": 0,
	},
	{
		"url_pattern": "^category/(?P<category_slug>[^/]+)$",
		"template_path": "pages/category/detail.html",
		"requires_auth": 0,
	},
]


def seed_default_routes():
	"""Add any missing default route. Idempotent, so install and the patch can both call it."""
	settings = frappe.get_single("Buzz Theme Settings")
	existing_patterns = {row.url_pattern for row in settings.routes}

	missing_routes = [route for route in DEFAULT_ROUTES if route["url_pattern"] not in existing_patterns]
	if not missing_routes:
		return

	for route in missing_routes:
		settings.append("routes", route)

	settings.save(ignore_permissions=True)


class BuzzThemeSettings(Document):
	def validate(self):
		for row in self.get("routes") or []:
			try:
				re.compile(row.url_pattern)
			except re.error as exc:
				frappe.throw(f"Invalid regex in route '{row.url_pattern}': {exc}")

	def on_update(self):
		clear_settings_cache()


def clear_settings_cache():
	frappe.cache.delete_value("buzz_theme_settings_compiled")
	frappe.local.buzz_theme_compiled_routes = None


def build_compiled_routes():
	settings = frappe.get_cached_doc("Buzz Theme Settings")
	compiled = []
	for row in settings.get("routes") or []:
		try:
			pattern = re.compile(row.url_pattern)
		except re.error:
			continue
		compiled.append(
			{
				"pattern": pattern,
				"template_path": row.template_path,
				"requires_auth": bool(row.requires_auth),
			}
		)
	return {
		"routes": compiled,
		"dynamic_pages_enabled": bool(settings.dynamic_pages_enabled),
	}


def get_compiled_routes():
	routes = getattr(frappe.local, "buzz_theme_compiled_routes", None)
	if routes is None:
		routes = frappe.cache.get_value("buzz_theme_settings_compiled", generator=build_compiled_routes)
		frappe.local.buzz_theme_compiled_routes = routes
	return routes
