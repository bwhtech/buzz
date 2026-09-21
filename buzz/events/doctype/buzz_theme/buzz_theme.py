# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.caching import redis_cache

from buzz.events.doctype.buzz_theme.tokens import REQUIRED_TOKENS, css_value, token_error

COLOR_SCHEMES = ("dark", "light")


class BuzzTheme(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.buzz_theme_token.buzz_theme_token import BuzzThemeToken

		color_scheme: DF.Literal["dark", "light"]
		enabled: DF.Check
		is_standard: DF.Check
		theme_name: DF.Data
		tokens: DF.Table[BuzzThemeToken]
	# end: auto-generated types

	def validate(self):
		self.validate_standard_theme()
		self.validate_tokens()
		self.validate_required_tokens()

	def validate_standard_theme(self):
		if self.is_standard and not can_change_standard_themes():
			frappe.throw(_("Standard themes cannot be changed. Duplicate the theme to customise it."))

	def validate_tokens(self):
		for row in self.tokens:
			if error := token_error(row.token, row.type, row.value):
				frappe.throw(_("Row {0}: {1}").format(row.idx, error))

	def validate_required_tokens(self):
		missing = sorted(set(REQUIRED_TOKENS) - {row.token for row in self.tokens})
		if missing:
			frappe.throw(_("Missing tokens: {0}").format(", ".join(missing)))

	def on_update(self):
		theme_css.clear_cache()

	def on_trash(self):
		self.validate_standard_theme()
		theme_css.clear_cache()


def can_change_standard_themes() -> bool:
	flags = frappe.flags
	return bool(frappe.conf.developer_mode or flags.in_import or flags.in_install or flags.in_migrate)


def resolve_theme(*candidates: str | None) -> str | None:
	"""First enabled theme among the candidates, else any enabled standard theme."""
	enabled = frappe.get_all(
		"Buzz Theme", filters={"enabled": 1}, pluck="name", order_by="is_standard desc, creation asc"
	)
	return next((name for name in candidates if name in enabled), enabled[0] if enabled else None)


@redis_cache(ttl=10 * 24 * 3600)
def theme_css(name: str) -> str:
	scheme = frappe.db.get_value("Buzz Theme", name, "color_scheme")
	rows = frappe.get_all(
		"Buzz Theme Token",
		filters={"parenttype": "Buzz Theme", "parent": name},
		fields=["token", "type", "value"],
		order_by="idx",
	)
	# Re-checked here too: a row written past validate (db.set_value, a data import) must not reach the page
	declarations = [
		f"--{row.token}: {css_value(row.type, row.value)};"
		for row in rows
		if not token_error(row.token, row.type, row.value)
	]
	color_scheme = scheme if scheme in COLOR_SCHEMES else COLOR_SCHEMES[0]
	return f":root {{ color-scheme: {color_scheme}; {' '.join(declarations)} }}"
