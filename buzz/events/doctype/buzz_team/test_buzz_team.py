# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team.buzz_team import create_default_team_for

OWNER = "team-owner@example.com"


def create_user(email: str, first_name: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	return email


class TestBuzzTeam(IntegrationTestCase):
	# Rollback is per class, not per test — every test needs its own team name and user.
	def setUp(self):
		frappe.set_user("Administrator")
		create_user(OWNER, "Team")

	def create_team(self, team_name: str) -> "frappe.Document":
		return frappe.get_doc({"doctype": "Buzz Team", "team_name": team_name}).insert()

	def owner_of(self, team: str) -> str | None:
		return frappe.db.get_value("Buzz Team Membership", {"team": team, "team_role": "Owner"}, "user")

	def test_name_is_a_bteam_series(self):
		team = self.create_team("Named Events")

		self.assertRegex(team.name, r"^BTEAM\d{4,}$")

	def test_slug_is_generated_from_team_name(self):
		team = self.create_team("Slug Events")

		self.assertEqual(team.slug, "slug-events")

	def test_creating_user_becomes_the_owner(self):
		frappe.set_user(OWNER)
		self.addCleanup(frappe.set_user, "Administrator")

		team = frappe.get_doc({"doctype": "Buzz Team", "team_name": "Session Events"}).insert(
			ignore_permissions=True
		)

		self.assertEqual(self.owner_of(team.name), OWNER)

	def test_owner_can_be_named_explicitly_for_another_user(self):
		team = frappe.get_doc({"doctype": "Buzz Team", "team_name": "Explicit Events"})
		team.flags.owner_user = OWNER
		team.insert()

		self.assertEqual(self.owner_of(team.name), OWNER)

	def test_generated_slug_is_deduplicated(self):
		first = self.create_team("Duplicate Events")
		second = self.create_team("Duplicate Events")

		self.assertEqual(first.slug, "duplicate-events")
		self.assertEqual(second.slug, "duplicate-events-1")

	def test_explicit_duplicate_slug_is_rejected(self):
		self.create_team("Taken Slug Events")

		clashing = frappe.get_doc(
			{"doctype": "Buzz Team", "team_name": "Other Events", "slug": "taken-slug-events"}
		)

		self.assertRaises(frappe.UniqueValidationError, clashing.insert)

	def test_slug_can_be_changed_after_insert(self):
		team = self.create_team("Renamed Events")

		team.slug = "renamed-conf"
		team.save()

		self.assertEqual(frappe.db.get_value("Buzz Team", team.name, "slug"), "renamed-conf")

	def test_default_team_is_named_after_the_user(self):
		user = create_user("default-team@example.com", "Priya")

		team = create_default_team_for(user)

		self.assertEqual(team.team_name, "Priya's Team")
		self.assertEqual(self.owner_of(team.name), user)

	def test_default_team_is_created_only_once(self):
		user = create_user("default-team-twice@example.com", "Rohan")

		create_default_team_for(user)
		create_default_team_for(user)

		self.assertEqual(frappe.db.count("Buzz Team Membership", {"user": user, "team_role": "Owner"}), 1)

	def test_default_teams_for_users_sharing_a_first_name_do_not_collide(self):
		first = create_user("default-team-sam-one@example.com", "Sam")
		second = create_user("default-team-sam-two@example.com", "Sam")

		create_default_team_for(first)
		create_default_team_for(second)

		self.assertEqual(frappe.db.count("Buzz Team", {"team_name": "Sam's Team"}), 2)

	def test_patch_gives_event_managers_a_team_and_is_idempotent(self):
		from buzz.patches.create_default_teams import execute

		user = create_user("patched-manager@example.com", "Patched")
		frappe.get_doc("User", user).add_roles("Event Manager")

		execute()
		execute()

		self.assertEqual(frappe.db.count("Buzz Team Membership", {"user": user, "team_role": "Owner"}), 1)

	def test_patch_skips_users_without_event_manager(self):
		from buzz.patches.create_default_teams import execute

		user = create_user("patched-outsider@example.com", "Outsider")

		execute()

		self.assertEqual(frappe.db.count("Buzz Team Membership", {"user": user, "team_role": "Owner"}), 0)

	def test_inserting_a_team_creates_one_owner_membership(self):
		team = frappe.get_doc({"doctype": "Buzz Team", "team_name": "Membership Events"})
		team.flags.owner_user = OWNER
		team.insert()

		memberships = frappe.get_all(
			"Buzz Team Membership",
			filters={"team": team.name},
			fields=["user", "team_role", "enabled"],
		)

		self.assertEqual(len(memberships), 1)
		self.assertEqual(memberships[0].user, OWNER)
		self.assertEqual(memberships[0].team_role, "Owner")
		self.assertEqual(memberships[0].enabled, 1)
