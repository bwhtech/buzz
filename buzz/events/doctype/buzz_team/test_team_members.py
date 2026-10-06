# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzTeamFactory, UserFactory

OWNER = "add-members-owner@example.com"


class TestAddMembers(IntegrationTestCase):
	def setUp(self):
		# Every added member is mailed, which needs an outgoing email account.
		self.sendmail = self.enterContext(patch("frappe.sendmail"))
		self.team = BuzzTeamFactory.create_owned_by(UserFactory.create_once(OWNER).name)

	def test_members_are_added_with_the_roles_given(self):
		manager = UserFactory.create_once("added-manager@example.com").name
		frontdesk = UserFactory.create_once("added-frontdesk@example.com").name

		added = self.add((manager, "Manager"), (frontdesk, "Frontdesk"))

		self.assertEqual(added, 2)
		self.assertEqual(self.membership_of(manager), {"team_role": "Manager", "enabled": 1})
		self.assertEqual(self.membership_of(frontdesk), {"team_role": "Frontdesk", "enabled": 1})

	def test_every_added_member_is_mailed(self):
		first = UserFactory.create_once("mailed-first@example.com").name
		second = UserFactory.create_once("mailed-second@example.com").name

		self.add((first, "Manager"), (second, "Viewer"))

		self.assertEqual(self.recipients(), [[first], [second]])

	def test_an_added_manager_earns_the_event_manager_role(self):
		user = UserFactory.create_once("added-earns-role@example.com").name

		self.add((user, "Manager"))

		self.assertIn("Event Manager", frappe.get_roles(user))

	def test_an_existing_member_is_left_alone_and_not_mailed(self):
		user = UserFactory.create_once("already-a-member@example.com").name
		self.add((user, "Admin"))
		self.sendmail.reset_mock()

		added = self.add((user, "Viewer"))

		self.assertEqual(added, 0)
		self.assertEqual(self.membership_of(user), {"team_role": "Admin", "enabled": 1})
		self.assertEqual(self.recipients(), [])

	def test_a_lapsed_membership_is_re_enabled_and_mailed(self):
		user = UserFactory.create_once("lapsed-member@example.com").name
		self.add((user, "Manager"))
		membership = frappe.get_doc("Buzz Team Membership", {"team": self.team.name, "user": user})
		membership.enabled = 0
		membership.save()
		self.sendmail.reset_mock()

		added = self.add((user, "Viewer"))

		self.assertEqual(added, 1)
		self.assertEqual(self.membership_of(user), {"team_role": "Viewer", "enabled": 1})
		self.assertEqual(self.recipients(), [[user]])

	def test_ownership_cannot_be_granted(self):
		user = UserFactory.create_once("cannot-own@example.com").name

		self.assertRaises(frappe.ValidationError, self.add, (user, "Owner"))

		self.assertIsNone(self.membership_of(user))

	def test_a_manager_cannot_add_members(self):
		manager = UserFactory.create_once("manager-adding@example.com").name
		self.add((manager, "Manager"))
		outsider = UserFactory.create_once("manager-adds-this@example.com").name

		with self.set_user(manager):
			self.assertRaises(frappe.PermissionError, self.add, (outsider, "Viewer"))

		self.assertIsNone(self.membership_of(outsider))

	def test_a_team_admin_can_add_members(self):
		admin = UserFactory.create_once("admin-adding@example.com").name
		self.add((admin, "Admin"))
		newcomer = UserFactory.create_once("admin-adds-this@example.com").name

		with self.set_user(admin):
			added = self.add((newcomer, "Viewer"))

		self.assertEqual(added, 1)
		self.assertEqual(self.membership_of(newcomer), {"team_role": "Viewer", "enabled": 1})

	def test_users_are_found_by_email(self):
		user = UserFactory.create_once("searched-by-email@example.com").name

		self.assertIn(user, self.found("searched-by-email"))

	def test_users_are_found_by_full_name(self):
		user = UserFactory.create(first_name="Priyanka", last_name="Chatterjee").name

		self.assertIn(user, self.found("Priyanka Chatterjee"))

	def test_website_users_are_found(self):
		user = UserFactory.create_once("website-user@example.com").name
		frappe.db.set_value("User", user, "user_type", "Website User")

		self.assertIn(user, self.found("website-user"))

	def test_existing_members_are_not_offered(self):
		user = UserFactory.create_once("already-searchable@example.com").name
		self.add((user, "Manager"))

		self.assertNotIn(user, self.found("already-searchable"))

	def test_disabled_users_are_not_offered(self):
		user = UserFactory.create_once("disabled-searchable@example.com").name
		frappe.db.set_value("User", user, "enabled", 0)
		self.addCleanup(frappe.db.set_value, "User", user, "enabled", 1)

		self.assertNotIn(user, self.found("disabled-searchable"))

	def test_administrator_and_guest_are_not_offered(self):
		self.assertNotIn("Administrator", self.found("Administrator"))
		self.assertNotIn("Guest", self.found("Guest"))

	def test_a_manager_cannot_search(self):
		manager = UserFactory.create_once("manager-searching@example.com").name
		self.add((manager, "Manager"))

		with self.set_user(manager):
			self.assertRaises(frappe.PermissionError, self.team.search_addable_users, "anything")

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

	def found(self, txt: str) -> list[str]:
		return [row["value"] for row in self.team.search_addable_users(txt)]
