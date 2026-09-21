from unittest.mock import patch

import frappe
from frappe.model.document import Document
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_theme.buzz_theme import resolve_theme, theme_css


def copy_of_classic(theme_name: str, **overrides) -> Document:
	classic = frappe.get_doc("Buzz Theme", "Classic")
	theme = frappe.copy_doc(classic)
	theme.update({"theme_name": theme_name, "is_standard": 0, **overrides})
	return theme


def set_token(theme, token: str, value: str, token_type: str | None = None):
	row = next(row for row in theme.tokens if row.token == token)
	row.value = value
	row.type = token_type or row.type


class TestBuzzTheme(IntegrationTestCase):
	def test_copy_of_standard_theme_saves(self):
		copy_of_classic("Copied Theme").insert()
		css = theme_css("Copied Theme")
		self.assertIn("--accent: light-dark(#171717, #ffffff);", css)
		self.assertIn(":root[data-mode=light] { color-scheme: light; }", css)

	def test_missing_token_is_rejected(self):
		theme = copy_of_classic("Missing Token Theme")
		theme.tokens = [row for row in theme.tokens if row.token != "accent"]
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_value_that_breaks_out_of_the_rule_is_rejected(self):
		theme = copy_of_classic("Injected Value Theme")
		set_token(theme, "accent", "red; } body { display: none } .x {")
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_dark_value_that_breaks_out_of_the_rule_is_rejected(self):
		theme = copy_of_classic("Injected Dark Theme")
		next(row for row in theme.tokens if row.token == "accent").dark_value = "red; } body { x: y"
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_required_colour_needs_a_dark_value(self):
		theme = copy_of_classic("No Dark Theme")
		next(row for row in theme.tokens if row.token == "accent").dark_value = ""
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_token_name_is_restricted(self):
		theme = copy_of_classic("Injected Name Theme")
		theme.append("tokens", {"token": "x: red; } body {", "type": "Color", "value": "#fff"})
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_font_must_come_from_the_allowlist(self):
		theme = copy_of_classic("Free Font Theme")
		set_token(theme, "font-body", "Comic Sans MS, cursive")
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_required_token_keeps_its_type(self):
		theme = copy_of_classic("Wrong Type Theme")
		set_token(theme, "radius", "#fff", "Color")
		self.assertRaises(frappe.ValidationError, theme.insert)

	def test_extra_tokens_are_allowed(self):
		theme = copy_of_classic("Extra Token Theme")
		theme.append("tokens", {"token": "highlight", "type": "Color", "value": "oklch(70% 0.1 200)"})
		theme.insert()
		self.assertIn("--highlight: oklch(70% 0.1 200);", theme_css("Extra Token Theme"))

	def test_standard_theme_is_read_only_outside_developer_mode(self):
		classic = frappe.get_doc("Buzz Theme", "Classic")
		with patch.dict(frappe.conf, {"developer_mode": 0}):
			self.assertRaises(frappe.ValidationError, classic.save)

	def test_rows_written_past_validation_never_render(self):
		theme = copy_of_classic("Tampered Theme").insert()
		row = next(row for row in theme.tokens if row.token == "accent")
		frappe.db.set_value("Buzz Theme Token", row.name, "value", "red; } body { display: none")
		theme_css.clear_cache()
		css = theme_css("Tampered Theme")
		self.assertNotIn("display: none", css)
		self.assertNotIn("--accent:", css)

	def test_resolve_theme_skips_disabled(self):
		copy_of_classic("Disabled Theme", enabled=0).insert()
		self.assertEqual(resolve_theme("Disabled Theme", "Paper"), "Paper")
		self.assertEqual(resolve_theme(None, "No Such Theme"), "Classic")
