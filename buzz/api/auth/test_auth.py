import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.auth import get_login_context


class TestGetLoginContext(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_returns_expected_keys(self):
		context = get_login_context().__json__()
		self.assertEqual(
			set(context),
			{
				"disable_signup",
				"disable_user_pass_login",
				"login_with_email_link",
				"login_banner",
				"provider_logins",
			},
		)

	def test_settings_flags_stay_integers(self):
		context = get_login_context().__json__()
		for key in ("disable_signup", "disable_user_pass_login", "login_with_email_link"):
			self.assertIsInstance(context[key], int)

	def test_banner_is_rendered_as_html(self):
		frappe.db.set_single_value("Buzz Settings", "login_banner", "# Welcome")
		self.addCleanup(frappe.db.set_single_value, "Buzz Settings", "login_banner", None)

		self.assertIn("<h1", get_login_context().__json__()["login_banner"])

	def test_banner_is_none_when_unset(self):
		frappe.db.set_single_value("Buzz Settings", "login_banner", None)

		self.assertIsNone(get_login_context().__json__()["login_banner"])

	def test_available_to_guest(self):
		frappe.set_user("Guest")

		self.assertIsInstance(get_login_context().__json__()["provider_logins"], list)
