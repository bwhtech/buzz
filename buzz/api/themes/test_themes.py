import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.themes import get_theme_options
from buzz.events.doctype.buzz_team.test_buzz_team import create_user


class TestGetThemeOptions(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_administrator_can_edit(self):
		options = get_theme_options()
		self.assertTrue(options.can_edit)
		self.assertIn("Inter", options.fonts)

	def test_team_member_cannot_edit(self):
		frappe.set_user(create_user("theme-reader@example.com", "Reader"))
		self.assertFalse(get_theme_options().can_edit)
