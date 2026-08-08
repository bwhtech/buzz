import re

import frappe
from frappe.model.document import Document


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
