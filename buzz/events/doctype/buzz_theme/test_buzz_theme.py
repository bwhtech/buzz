from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_theme.buzz_theme import resolve_theme, theme_css
from buzz.tests.factories.events.buzz_theme_factory import BuzzThemeFactory


class TestBuzzTheme(IntegrationTestCase):
	def test_copy_of_standard_theme_saves(self):
		theme = BuzzThemeFactory.create()
		css = theme_css(theme.name)
		self.assertIn("--accent: light-dark(#171717, #ffffff);", css)
		self.assertIn(":root[data-mode=light] { color-scheme: light; }", css)

	def test_missing_token_is_rejected(self):
		theme = BuzzThemeFactory.build()
		theme.tokens = [row for row in theme.tokens if row.token != "accent"]
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_value_that_breaks_out_of_the_rule_is_rejected(self):
		theme = BuzzThemeFactory.build()
		set_token(theme, "accent", "red; } body { display: none } .x {")
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_dark_value_that_breaks_out_of_the_rule_is_rejected(self):
		theme = BuzzThemeFactory.build()
		token_row(theme, "accent").dark_value = "red; } body { x: y"
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_required_colour_needs_a_dark_value(self):
		theme = BuzzThemeFactory.build()
		token_row(theme, "accent").dark_value = ""
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_token_name_is_restricted(self):
		theme = BuzzThemeFactory.build()
		theme.append("tokens", {"token": "x: red; } body {", "type": "Color", "value": "#fff"})
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_font_must_come_from_the_allowlist(self):
		theme = BuzzThemeFactory.build()
		set_token(theme, "font-body", "Comic Sans MS, cursive")
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_required_token_keeps_its_type(self):
		theme = BuzzThemeFactory.build()
		set_token(theme, "radius", "#fff", "Color")
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_extra_tokens_are_allowed(self):
		theme = BuzzThemeFactory.build()
		theme.append("tokens", {"token": "highlight", "type": "Color", "value": "oklch(70% 0.1 200)"})
		theme.insert()
		self.assertIn("--highlight: oklch(70% 0.1 200);", theme_css(theme.name))

	def test_standard_theme_is_read_only_outside_developer_mode(self):
		classic = frappe.get_doc("Buzz Theme", "Classic")
		with patch.dict(frappe.conf, {"developer_mode": 0}):
			self.assertRaises(frappe.ValidationError, classic.save)

	def test_rows_written_past_validation_never_render(self):
		theme = BuzzThemeFactory.create()
		frappe.db.set_value(
			"Buzz Theme Token", token_row(theme, "accent").name, "value", "red; } body { display: none"
		)
		theme_css.clear_cache()
		css = theme_css(theme.name)
		self.assertNotIn("display: none", css)
		self.assertNotIn("--accent:", css)

	def test_resolve_theme_skips_disabled(self):
		theme = BuzzThemeFactory.create(enabled=0)
		self.assertEqual(resolve_theme(theme.name, "Paper"), "Paper")
		self.assertEqual(resolve_theme(None, "No Such Theme"), "Classic")


def token_row(theme, token: str):
	return next(row for row in theme.tokens if row.token == token)


def set_token(theme, token: str, value: str, token_type: str | None = None):
	row = token_row(theme, token)
	row.value = value
	row.type = token_type or row.type
