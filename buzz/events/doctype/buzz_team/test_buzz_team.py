# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team.buzz_team import create_default_team_for
from buzz.patches.assign_default_team import TEAM_DIRECT_DOCTYPES

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


def create_owned_team(team_name: str, owner: str) -> str:
	team = frappe.get_doc({"doctype": "Buzz Team", "team_name": team_name})
	team.flags.owner_user = owner
	return team.insert(ignore_permissions=True).name


def payload_for(doctype: str, suffix: str) -> dict:
	payloads = {
		"Event Venue": {"name": f"Venue {suffix}", "address": "somewhere"},
		"Event Host": {"name": f"Host {suffix}"},
		"Event Template": {"template_name": f"Template {suffix}"},
		"Buzz Campaign": {"name": f"Campaign {suffix}", "title": suffix, "description": "why"},
		"Buzz Event": {
			"title": f"Event {suffix}",
			"category": "Test Category",
			"host": "Test Host",
			"start_date": "2026-03-05",
			"end_date": "2026-03-06",
			"start_time": "09:00:00",
			"end_time": "18:00:00",
		},
	}
	return {"doctype": doctype, **payloads[doctype]}


class TestSetTeamFromSoleMembership(IntegrationTestCase):
	# Rollback is per class, not per test — every test owns its user and its team names.
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def insert_as(self, user: str, doctype: str, suffix: str, **overrides):
		frappe.set_user(user)
		return frappe.get_doc({**payload_for(doctype, suffix), **overrides}).insert(ignore_permissions=True)

	def test_stamps_the_users_only_team(self):
		user = create_user("one-team@example.com", "Tenant")
		team = create_owned_team("One Team", user)

		for doctype in TEAM_DIRECT_DOCTYPES:
			with self.subTest(doctype=doctype):
				doc = self.insert_as(user, doctype, f"Only {doctype}")

				self.assertEqual(doc.team, team)

	def test_leaves_team_empty_when_the_user_has_two_teams(self):
		user = create_user("two-teams@example.com", "Tenant")
		create_owned_team("Two Teams A", user)
		create_owned_team("Two Teams B", user)

		with self.assertRaises(frappe.MandatoryError):
			self.insert_as(user, "Event Venue", "Ambiguous")

	def test_explicit_team_wins_for_a_multi_team_user(self):
		user = create_user("picks-a-team@example.com", "Tenant")
		create_owned_team("Picks A", user)
		chosen = create_owned_team("Picks B", user)

		doc = self.insert_as(user, "Event Venue", "Chosen", team=chosen)

		self.assertEqual(doc.team, chosen)

	def test_explicit_team_is_never_overwritten(self):
		user = create_user("single-team-override@example.com", "Tenant")
		create_owned_team("Overridden Home", user)
		other = create_owned_team("Overridden Other", create_user("other-owner@example.com", "Tenant"))

		doc = self.insert_as(user, "Event Venue", "Override", team=other)

		self.assertEqual(doc.team, other)

	def test_disabled_membership_does_not_count(self):
		user = create_user("disabled-member@example.com", "Tenant")
		enabled = create_owned_team("Disabled Enabled", user)
		spare = create_owned_team("Disabled Spare", create_user("spare-owner@example.com", "Tenant"))
		membership = frappe.get_doc(
			{"doctype": "Buzz Team Membership", "team": spare, "user": user, "team_role": "Manager"}
		).insert(ignore_permissions=True)
		membership.enabled = 0
		membership.save(ignore_permissions=True)

		doc = self.insert_as(user, "Event Venue", "Disabled")

		self.assertEqual(doc.team, enabled)
