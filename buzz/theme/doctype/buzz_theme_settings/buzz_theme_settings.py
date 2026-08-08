import re

import frappe
from frappe.model.document import Document


class BuzzThemeSettings(Document):
	def validate(self):
		# Reject bad patterns before the row is written, so a route can never
		# reach the compiled-routes cache (where a bad one would be silently
		# skipped) in the first place.
		for row in self.get("routes") or []:
			try:
				re.compile(row.url_pattern)
			except re.error as exc:
				frappe.throw(f"Invalid regex in route '{row.url_pattern}': {exc}")

	def on_update(self):
		clear_settings_cache()


def clear_settings_cache():
	frappe.cache.delete_value("buzz_theme_settings_compiled")


def get_compiled_routes():
	def _build():
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

	return frappe.cache.get_value("buzz_theme_settings_compiled", generator=_build)
