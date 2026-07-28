import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.account import get_enabled_languages, get_user_info, update_user_language
from buzz.api.exceptions import BuzzAPIError


class TestGetUserInfo(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_guest_payload_carries_only_two_keys(self):
		frappe.set_user("Guest")
		info = get_user_info().__json__()

		self.assertEqual(set(info), {"is_logged_in", "brand_image"})
		self.assertFalse(info["is_logged_in"])

	def test_logged_in_payload_shape(self):
		info = get_user_info().__json__()

		self.assertEqual(
			set(info),
			{
				"name",
				"is_logged_in",
				"first_name",
				"last_name",
				"full_name",
				"email",
				"user_image",
				"roles",
				"brand_image",
				"language",
			},
		)
		self.assertTrue(info["is_logged_in"])
		self.assertEqual(info["name"], "Administrator")

	def test_roles_stay_child_table_rows(self):
		roles = get_user_info().__json__()["roles"]

		self.assertTrue(roles)
		self.assertTrue(any(row.role == "Administrator" for row in roles))


class TestLanguages(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_enabled_languages_shape(self):
		languages = [language.__json__() for language in get_enabled_languages()]

		self.assertTrue(languages)
		self.assertEqual(set(languages[0]), {"name", "language_name", "language_code"})

	def test_update_rejects_unknown_language(self):
		with self.assertRaises(BuzzAPIError):
			update_user_language("not-a-language")

	def test_unknown_language_maps_to_400(self):
		self.assertEqual(BuzzAPIError.http_status_code, 400)

	def test_update_persists_language(self):
		original = frappe.db.get_value("User", "Administrator", "language")
		self.addCleanup(frappe.db.set_value, "User", "Administrator", "language", original)

		update_user_language("en")

		self.assertEqual(frappe.db.get_value("User", "Administrator", "language"), "en")
