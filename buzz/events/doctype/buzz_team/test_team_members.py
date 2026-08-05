# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user

OWNER = "add-members-owner@example.com"


class TestAddMembers(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		# Every added member is mailed, which needs an outgoing email account.
		self.sendmail = self.enterContext(patch("frappe.sendmail"))
		self.team = frappe.get_doc(
			"Buzz Team", create_owned_team(self.unique_name(), create_user(OWNER, "Owner"))
		)

	def unique_name(self) -> str:
		return f"Members Team {frappe.generate_hash(length=6)}"

	def add(self, *members: tuple[str, str]) -> int:
		payload = [{"user": user, "team_role": team_role} for user, team_role in members]
		return self.team.add_members(frappe.as_json(payload))

	def membership_of(self, user: str) -> dict | None:
		return frappe.db.get_value(
			"Buzz Team Membership",
			{"team": self.team.name, "user": user},
			["team_role", "enabled"],
			as_dict=True,
		)

	def recipients(self) -> list[str]:
		return [call.kwargs["recipients"] for call in self.sendmail.call_args_list]

	def test_members_are_added_with_the_roles_given(self):
		manager = create_user("added-manager@example.com", "Manager")
		frontdesk = create_user("added-frontdesk@example.com", "Frontdesk")

		added = self.add((manager, "Manager"), (frontdesk, "Frontdesk"))

		self.assertEqual(added, 2)
		self.assertEqual(self.membership_of(manager), {"team_role": "Manager", "enabled": 1})
		self.assertEqual(self.membership_of(frontdesk), {"team_role": "Frontdesk", "enabled": 1})

	def test_every_added_member_is_mailed(self):
		first = create_user("mailed-first@example.com", "First")
		second = create_user("mailed-second@example.com", "Second")

		self.add((first, "Manager"), (second, "Viewer"))

		self.assertEqual(self.recipients(), [[first], [second]])

	def test_an_added_manager_earns_the_event_manager_role(self):
		user = create_user("added-earns-role@example.com", "Earner")

		self.add((user, "Manager"))

		self.assertIn("Event Manager", frappe.get_roles(user))

	def test_an_existing_member_is_left_alone_and_not_mailed(self):
		user = create_user("already-a-member@example.com", "Member")
		self.add((user, "Admin"))
		self.sendmail.reset_mock()

		added = self.add((user, "Viewer"))

		self.assertEqual(added, 0)
		self.assertEqual(self.membership_of(user), {"team_role": "Admin", "enabled": 1})
		self.assertEqual(self.recipients(), [])

	def test_a_lapsed_membership_is_re_enabled_and_mailed(self):
		user = create_user("lapsed-member@example.com", "Lapsed")
		self.add((user, "Manager"))
		membership = frappe.get_doc("Buzz Team Membership", {"team": self.team.name, "user": user})
		membership.enabled = 0
		membership.save(ignore_permissions=True)
		self.sendmail.reset_mock()

		added = self.add((user, "Viewer"))

		self.assertEqual(added, 1)
		self.assertEqual(self.membership_of(user), {"team_role": "Viewer", "enabled": 1})
		self.assertEqual(self.recipients(), [[user]])

	def test_ownership_cannot_be_granted(self):
		user = create_user("cannot-own@example.com", "Pretender")

		self.assertRaises(frappe.ValidationError, self.add, (user, "Owner"))

		self.assertIsNone(self.membership_of(user))

	def test_a_manager_cannot_add_members(self):
		manager = create_user("manager-adding@example.com", "Manager")
		self.add((manager, "Manager"))
		outsider = create_user("manager-adds-this@example.com", "Outsider")
		frappe.set_user(manager)

		self.assertRaises(frappe.PermissionError, self.add, (outsider, "Viewer"))

		frappe.set_user("Administrator")
		self.assertIsNone(self.membership_of(outsider))

	def found(self, txt: str) -> list[str]:
		return [row["value"] for row in self.team.search_addable_users(txt)]

	def test_users_are_found_by_email(self):
		user = create_user("searched-by-email@example.com", "Searched")

		self.assertIn(user, self.found("searched-by-email"))

	def test_users_are_found_by_full_name(self):
		user = create_user("found-by-name@example.com", "Priyanka")
		frappe.db.set_value("User", user, "last_name", "Chatterjee")
		frappe.db.set_value("User", user, "full_name", "Priyanka Chatterjee")

		self.assertIn(user, self.found("Priyanka Chatterjee"))

	def test_website_users_are_found(self):
		user = create_user("website-user@example.com", "Attendee")
		frappe.db.set_value("User", user, "user_type", "Website User")

		self.assertIn(user, self.found("website-user"))

	def test_existing_members_are_not_offered(self):
		user = create_user("already-searchable@example.com", "Existing")
		self.add((user, "Manager"))

		self.assertNotIn(user, self.found("already-searchable"))

	def test_disabled_users_are_not_offered(self):
		user = create_user("disabled-searchable@example.com", "Disabled")
		frappe.db.set_value("User", user, "enabled", 0)
		self.addCleanup(frappe.db.set_value, "User", user, "enabled", 1)

		self.assertNotIn(user, self.found("disabled-searchable"))

	def test_administrator_and_guest_are_not_offered(self):
		self.assertNotIn("Administrator", self.found("Administrator"))
		self.assertNotIn("Guest", self.found("Guest"))

	def test_a_manager_cannot_search(self):
		manager = create_user("manager-searching@example.com", "Manager")
		self.add((manager, "Manager"))
		frappe.set_user(manager)

		self.assertRaises(frappe.PermissionError, self.team.search_addable_users, "anything")

	def test_a_team_admin_can_add_members(self):
		admin = create_user("admin-adding@example.com", "Admin")
		self.add((admin, "Admin"))
		newcomer = create_user("admin-adds-this@example.com", "Newcomer")
		frappe.set_user(admin)

		added = self.add((newcomer, "Viewer"))

		frappe.set_user("Administrator")
		self.assertEqual(added, 1)
		self.assertEqual(self.membership_of(newcomer), {"team_role": "Viewer", "enabled": 1})
