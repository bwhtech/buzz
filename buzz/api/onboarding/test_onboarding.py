import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.account import get_user_info
from buzz.api.onboarding import check_username, complete_onboarding, save_profile
from buzz.api.onboarding.exceptions import InvalidUsername, UsernameTaken
from buzz.api.onboarding.services import STATUS_FIELD, mark_pending_on_signup
from buzz.tests.factories import UserFactory


class TestOnboarding(IntegrationTestCase):
	def setUp(self):
		self.user = UserFactory.create_once("onboarding-new@example.com")
		self.other = UserFactory.create_once("onboarding-other@example.com")
		frappe.db.set_value("User", self.other.name, "username", "taken-name")
		frappe.db.set_value("User", self.user.name, STATUS_FIELD, None)
		self.enterContext(self.change_settings("Buzz Settings", enable_onboarding=1))
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(self.user.name)

	def status(self) -> str | None:
		return frappe.db.get_value("User", self.user.name, STATUS_FIELD)

	def test_signup_is_pending_only_while_enabled(self):
		mark_pending_on_signup(self.user)
		self.assertEqual(self.status(), "Pending")

		frappe.db.set_value("User", self.user.name, STATUS_FIELD, None)
		with self.change_settings("Buzz Settings", enable_onboarding=0):
			mark_pending_on_signup(self.user)
		self.assertIsNone(self.status())

	def test_user_info_reports_onboarding_until_completed(self):
		self.assertFalse(get_user_info().needs_onboarding)

		mark_pending_on_signup(self.user)
		self.assertTrue(get_user_info().needs_onboarding)

		complete_onboarding()
		self.assertEqual(self.status(), "Completed")
		self.assertFalse(get_user_info().needs_onboarding)

	def test_username_availability(self):
		self.assertFalse(check_username("taken-name").available)
		self.assertFalse(check_username("No Caps").available)
		self.assertTrue(check_username("free-name").available)

	def test_save_profile_rejects_taken_and_invalid_usernames(self):
		with self.assertRaises(UsernameTaken):
			save_profile(first_name="Priya", username="taken-name")
		with self.assertRaises(InvalidUsername):
			save_profile(first_name="Priya", username="a")

	def test_save_profile_updates_user(self):
		save_profile(first_name="Priya", last_name="Raman", username="priya-onboarding")
		saved = frappe.db.get_value(
			"User", self.user.name, ["first_name", "last_name", "username"], as_dict=True
		)
		self.assertEqual(saved, {"first_name": "Priya", "last_name": "Raman", "username": "priya-onboarding"})
