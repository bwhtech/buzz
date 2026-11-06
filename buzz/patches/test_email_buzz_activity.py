import frappe
from frappe.tests import IntegrationTestCase

from buzz.patches.email_buzz_activity import execute
from buzz.tests.factories import UserFactory


class TestEmailBuzzActivity(IntegrationTestCase):
	def email_types(self, user: str) -> list[str]:
		frappe.clear_document_cache("Notification Settings", user)
		settings = frappe.get_doc("Notification Settings", user)
		return [row.notification_type for row in settings.email_notification_types]

	def set_email_types(self, user: str, types: list[str]) -> None:
		settings = frappe.get_doc("Notification Settings", user)
		settings.set("email_notification_types", [{"notification_type": name} for name in types])
		settings.save(ignore_permissions=True)

	def test_adds_buzz_activity_unless_the_user_opted_out_of_all_email(self):
		existing = UserFactory.create_once("email-patch-existing@example.com").name
		opted_out = UserFactory.create_once("email-patch-opted-out@example.com").name
		self.set_email_types(existing, ["Mention"])
		self.set_email_types(opted_out, [])

		execute()
		execute()

		self.assertEqual(self.email_types(existing), ["Mention", "Buzz Activity"])
		self.assertEqual(self.email_types(opted_out), [])
