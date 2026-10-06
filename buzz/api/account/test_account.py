from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.translate import get_all_languages
from frappe.utils import set_request

from buzz.api.account import (
	get_translations,
	get_user_info,
	update_user_language,
	update_user_timezone,
)
from buzz.api.account.exceptions import UnknownLanguage, UnknownTimezone
from buzz.api.account.services import get_default_language


class LanguageTestCase(IntegrationTestCase):
	"""`get_language` reads cookies and headers off the live request, which a test process lacks."""

	def install_request(self, cookies: dict[str, str] | None = None, accept_language: str = ""):
		headers = {}
		if cookies:
			headers["Cookie"] = "; ".join(f"{key}={value}" for key, value in cookies.items())
		if accept_language:
			headers["Accept-Language"] = accept_language

		set_request(method="GET", path="/api/method/get_translations", headers=headers)
		self.addCleanup(setattr, frappe.local, "request", None)

	def other_enabled_language(self) -> str:
		"""Plain codes only: werkzeug rewrites a regional one like `pt-BR` when it parses the header."""
		for language in get_all_languages():
			if language != get_default_language() and language.isalpha():
				return language

		self.skipTest("site has no second enabled language with a plain code")

	def set_user_language(self, language: str | None):
		original = frappe.db.get_value("User", "Administrator", "language")
		self.addCleanup(frappe.db.set_value, "User", "Administrator", "language", original)
		frappe.db.set_value("User", "Administrator", "language", language)


class TestGetUserInfo(LanguageTestCase):
	def test_guest_payload_keys(self):
		self.install_request()
		with self.set_user("Guest"):
			info = get_user_info().__json__()

		self.assertEqual(set(info), {"is_logged_in", "brand_image", "language"})
		self.assertFalse(info["is_logged_in"])

	def test_guest_language_follows_the_preferred_language_cookie(self):
		language = self.other_enabled_language()
		self.install_request(cookies={"preferred_language": language})

		with self.set_user("Guest"):
			self.assertEqual(get_user_info().__json__()["language"], language)

	def test_guest_language_falls_back_to_the_site_default(self):
		self.install_request()

		with self.set_user("Guest"):
			self.assertEqual(get_user_info().__json__()["language"], get_default_language())

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
				"bio",
				"roles",
				"brand_image",
				"language",
				"time_zone",
			},
		)
		self.assertTrue(info["is_logged_in"])
		self.assertEqual(info["name"], "Administrator")


class TestLanguages(LanguageTestCase):
	def test_update_rejects_unknown_language(self):
		frappe.clear_messages()

		with self.assertRaises(UnknownLanguage):
			update_user_language("not-a-language")

		message = frappe.local.message_log[-1]
		self.assertEqual(message["title"], "Language Not Available")
		self.assertIn("not-a-language", message["message"])

	def test_update_persists_language(self):
		self.set_user_language(None)

		update_user_language("en")

		self.assertEqual(frappe.db.get_value("User", "Administrator", "language"), "en")

	def test_update_stays_closed_to_guests(self):
		self.assertIn(update_user_language, frappe.whitelisted)
		self.assertNotIn(update_user_language, frappe.guest_methods)


class TestTimezones(IntegrationTestCase):
	def test_update_rejects_unknown_timezone(self):
		frappe.clear_messages()

		with self.assertRaises(UnknownTimezone):
			update_user_timezone("Mars/Olympus_Mons")

		message = frappe.local.message_log[-1]
		self.assertEqual(message["title"], "Timezone Not Available")
		self.assertIn("Mars/Olympus_Mons", message["message"])

	def test_update_persists_timezone(self):
		self.set_user_timezone(None)

		update_user_timezone("Asia/Kolkata")

		self.assertEqual(frappe.db.get_value("User", "Administrator", "time_zone"), "Asia/Kolkata")

	def test_update_accepts_utc(self):
		# The dashboard's picker puts UTC at the top of the list.
		self.set_user_timezone(None)

		update_user_timezone("UTC")

		self.assertEqual(frappe.db.get_value("User", "Administrator", "time_zone"), "UTC")

	def test_update_stays_closed_to_guests(self):
		self.assertIn(update_user_timezone, frappe.whitelisted)
		self.assertNotIn(update_user_timezone, frappe.guest_methods)

	def set_user_timezone(self, time_zone: str | None):
		original = frappe.db.get_value("User", "Administrator", "time_zone")
		self.addCleanup(frappe.db.set_value, "User", "Administrator", "time_zone", original)
		frappe.db.set_value("User", "Administrator", "time_zone", time_zone)


class TestGetTranslations(LanguageTestCase):
	def test_guest_translations_follow_the_preferred_language_cookie(self):
		language = self.other_enabled_language()
		self.install_request(cookies={"preferred_language": language})

		with self.set_user("Guest"):
			self.assertEqual(self.resolved_language(), language)

	def test_guest_translations_fall_back_to_the_accept_language_header(self):
		language = self.other_enabled_language()
		self.install_request(accept_language=language)

		with self.set_user("Guest"):
			self.assertEqual(self.resolved_language(), language)

	def test_guest_translations_fall_back_to_the_site_default(self):
		self.install_request()

		with self.set_user("Guest"):
			self.assertEqual(self.resolved_language(), get_default_language())

	def test_logged_in_translations_follow_the_user_document(self):
		language = self.other_enabled_language()
		self.set_user_language(language)

		self.assertEqual(self.resolved_language(), language)

	def test_a_user_without_a_language_gets_the_site_default(self):
		self.set_user_language(None)

		self.assertEqual(self.resolved_language(), get_default_language())

	def resolved_language(self) -> str:
		"""The language get_translations picked, without loading any."""
		with patch("buzz.api.account.get_all_translations", return_value={}) as translations:
			get_translations()

		translations.assert_called_once()
		return translations.call_args.args[0]
