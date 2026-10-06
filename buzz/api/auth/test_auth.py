from frappe.tests import IntegrationTestCase

from buzz.api.auth import get_login_context


class TestGetLoginContext(IntegrationTestCase):
	def test_banner_is_rendered_as_html(self):
		with self.change_settings("Buzz Settings", login_banner="# Welcome"):
			self.assertIn("<h1", get_login_context().__json__()["login_banner"])

	def test_banner_is_none_when_unset(self):
		with self.change_settings("Buzz Settings", login_banner=None):
			self.assertIsNone(get_login_context().__json__()["login_banner"])

	def test_available_to_guest(self):
		with self.set_user("Guest"):
			self.assertIsInstance(get_login_context().__json__()["provider_logins"], list)
