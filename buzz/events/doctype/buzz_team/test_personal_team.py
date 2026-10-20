# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team.buzz_team import create_personal_team_for, personal_team_of
from buzz.events.doctype.buzz_team_membership.buzz_team_membership import upsert_membership
from buzz.tests.factories import BuzzTeamFactory, UserFactory


class TestPersonalTeam(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.user = UserFactory.create_once("personal-team-owner@example.com").name

	def test_personal_team_is_owned_by_the_user(self):
		team = create_personal_team_for(self.user)

		self.assertTrue(team.is_personal)
		self.assertEqual(self.members_of(team.name), [(self.user, "Owner")])

	def test_personal_team_is_created_only_once(self):
		first = create_personal_team_for(self.user)
		second = create_personal_team_for(self.user)

		self.assertEqual(first.name, second.name)

	def test_owner_of_a_community_still_gets_a_personal_team(self):
		user = UserFactory.create().name
		community = BuzzTeamFactory.create_owned_by(user, "community")

		team = create_personal_team_for(user)

		self.assertNotEqual(team.name, community.name)

	def test_personal_team_is_never_published(self):
		team = create_personal_team_for(self.user)

		team.is_published = 1
		team.accept_community_submissions = 1
		team.save()

		self.assertEqual(
			frappe.db.get_value("Buzz Team", team.name, ["is_published", "accept_community_submissions"]),
			(0, 0),
		)

	def test_personal_team_takes_no_second_member(self):
		team = create_personal_team_for(self.user)
		other = UserFactory.create_once("personal-team-guest@example.com").name

		self.assertRaises(frappe.ValidationError, upsert_membership, team.name, other, "Admin")

	def test_personal_flag_cannot_be_cleared(self):
		team = create_personal_team_for(self.user)

		team.is_personal = 0

		self.assertRaises(frappe.CannotChangeConstantError, team.save)

	def test_blank_username_is_filled_with_a_unique_one(self):
		first_name = f"Wren{frappe.generate_hash(length=4)}"
		taken = UserFactory.create(first_name=first_name)
		blank = UserFactory.create(first_name=first_name)
		self.assertFalse(blank.username)

		create_personal_team_for(blank.name)

		username = frappe.db.get_value("User", blank.name, "username")
		self.assertTrue(username.startswith(frappe.scrub(first_name)))
		self.assertNotEqual(username, taken.username)

	def test_existing_username_is_kept(self):
		username = f"kept-{frappe.generate_hash(length=6)}"
		user = UserFactory.create(username=username)

		create_personal_team_for(user.name)

		self.assertEqual(frappe.db.get_value("User", user.name, "username"), username)

	def test_new_user_gets_a_personal_team_when_signup_creation_is_on(self):
		with self.change_settings("Buzz Settings", enable_personal_teams=1, create_personal_team_on_signup=1):
			user = UserFactory.create().name

		self.assertTrue(personal_team_of(user))

	def test_new_user_gets_no_personal_team_when_signup_creation_is_off(self):
		with self.change_settings("Buzz Settings", enable_personal_teams=1, create_personal_team_on_signup=0):
			user = UserFactory.create().name

		self.assertIsNone(personal_team_of(user))

	def test_new_user_gets_no_personal_team_when_personal_teams_are_off(self):
		with self.change_settings("Buzz Settings", enable_personal_teams=0, create_personal_team_on_signup=1):
			user = UserFactory.create().name

		self.assertIsNone(personal_team_of(user))

	def members_of(self, team: str) -> list[tuple]:
		return [
			tuple(row)
			for row in frappe.get_all(
				"Buzz Team Membership", filters={"team": team}, fields=["user", "team_role"], as_list=True
			)
		]
