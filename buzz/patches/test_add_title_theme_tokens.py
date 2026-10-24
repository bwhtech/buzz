import frappe
from frappe.tests import IntegrationTestCase

from buzz.patches.add_title_theme_tokens import execute
from buzz.tests.factories import BuzzThemeFactory


class TestAddTitleThemeTokens(IntegrationTestCase):
	def test_custom_theme_gets_missing_title_tokens(self):
		theme = BuzzThemeFactory.create()
		frappe.db.delete(
			"Buzz Theme Token", {"parent": theme.name, "token": ("in", ["font-title", "title-size"])}
		)
		execute()
		tokens = dict(
			frappe.get_all(
				"Buzz Theme Token", filters={"parent": theme.name}, fields=["token", "value"], as_list=True
			)
		)
		self.assertEqual(tokens["font-title"], "League Gothic")
		self.assertEqual(tokens["title-size"], "40px")
