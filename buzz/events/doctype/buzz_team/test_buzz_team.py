# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team.buzz_team import create_default_team_for
from buzz.patches.assign_default_team import TEAM_DIRECT_DOCTYPES
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventHostFactory,
	EventVenueFactory,
	UserFactory,
)
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import PAID_EVENTS_FLAG

OWNER = "team-owner@example.com"
TEAM_DIRECT_FACTORIES = {
	"Buzz Event": BuzzEventFactory,
	"Event Venue": EventVenueFactory,
	"Event Host": EventHostFactory,
}


class TestBuzzTeam(IntegrationTestCase):
	# Rollback is per class, not per test — every test needs its own team name.
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once(OWNER).name

	def test_slug_is_generated_from_team_name(self):
		team = self.create_team("Slug Events")

		self.assertEqual(team.slug, "slug-events")

	def test_creating_user_becomes_the_owner(self):
		with self.set_user(self.owner):
			team = BuzzTeamFactory.create(flags={"ignore_permissions": True})

		self.assertEqual(self.owner_of(team.name), self.owner)

	def test_owner_can_be_named_explicitly_for_another_user(self):
		team = BuzzTeamFactory.create(flags={"owner_user": self.owner})

		self.assertEqual(self.owner_of(team.name), self.owner)

	def test_generated_slug_is_deduplicated(self):
		first = self.create_team("Duplicate Events")
		second = self.create_team("Duplicate Events")

		self.assertEqual(first.slug, "duplicate-events")
		self.assertEqual(second.slug, "duplicate-events-1")

	def test_explicit_duplicate_slug_is_rejected(self):
		self.create_team("Taken Slug Events")

		clashing = BuzzTeamFactory.build(slug="taken-slug-events", flags={"owner_user": self.owner})

		self.assertRaises(frappe.UniqueValidationError, clashing.insert)

	def test_slug_can_be_changed_after_insert(self):
		team = self.create_team("Renamed Events")

		team.slug = "renamed-conf"
		team.save()

		self.assertEqual(frappe.db.get_value("Buzz Team", team.name, "slug"), "renamed-conf")

	def test_default_team_is_named_after_the_user(self):
		user = UserFactory.create(first_name="Priya").name

		team = create_default_team_for(user)

		self.assertEqual(team.team_name, "Priya's Team")
		self.assertEqual(self.owner_of(team.name), user)

	def test_default_team_is_created_only_once(self):
		user = UserFactory.create().name

		create_default_team_for(user)
		create_default_team_for(user)

		self.assertEqual(frappe.db.count("Buzz Team Membership", {"user": user, "team_role": "Owner"}), 1)

	def test_default_teams_for_users_sharing_a_first_name_do_not_collide(self):
		first = create_default_team_for(UserFactory.create(first_name="Sam").name)
		second = create_default_team_for(UserFactory.create(first_name="Sam").name)

		self.assertNotEqual(first.name, second.name)
		self.assertEqual({first.team_name, second.team_name}, {"Sam's Team"})

	def test_inserting_a_team_creates_one_owner_membership(self):
		team = BuzzTeamFactory.create(flags={"owner_user": self.owner})

		memberships = frappe.get_all(
			"Buzz Team Membership",
			filters={"team": team.name},
			fields=["user", "team_role", "enabled"],
		)

		self.assertEqual(len(memberships), 1)
		self.assertEqual(memberships[0].user, self.owner)
		self.assertEqual(memberships[0].team_role, "Owner")
		self.assertEqual(memberships[0].enabled, 1)

	def create_team(self, team_name: str):
		return BuzzTeamFactory.create_owned_by(self.owner, team_name=team_name)

	def owner_of(self, team: str) -> str | None:
		return frappe.db.get_value("Buzz Team Membership", {"team": team, "team_role": "Owner"}, "user")


class TestSetTeamFromSoleMembership(IntegrationTestCase):
	# Rollback is per class, not per test — every test owns its user.
	def test_stamps_the_users_only_team(self):
		user = UserFactory.create_once("one-team@example.com").name
		team = BuzzTeamFactory.create_owned_by(user).name

		for doctype in TEAM_DIRECT_DOCTYPES:
			with self.subTest(doctype=doctype):
				doc = self.insert_as(user, self.build_without_team(doctype, team))

				self.assertEqual(doc.team, team)

	def test_leaves_team_empty_when_the_user_has_two_teams(self):
		user = UserFactory.create_once("two-teams@example.com").name
		first = BuzzTeamFactory.create_owned_by(user).name
		BuzzTeamFactory.create_owned_by(user)

		doc = self.insert_as(user, self.build_without_team("Event Venue", first))

		self.assertFalse(doc.team)

	def test_explicit_team_wins_for_a_multi_team_user(self):
		user = UserFactory.create_once("picks-a-team@example.com").name
		BuzzTeamFactory.create_owned_by(user)
		chosen = BuzzTeamFactory.create_owned_by(user).name

		doc = self.insert_as(user, EventVenueFactory.build(team=chosen))

		self.assertEqual(doc.team, chosen)

	def test_explicit_team_is_never_overwritten(self):
		user = UserFactory.create_once("single-team-override@example.com").name
		BuzzTeamFactory.create_owned_by(user)
		other = BuzzTeamFactory.create_owned_by(UserFactory.create_once("other-owner@example.com").name).name

		doc = self.insert_as(user, EventVenueFactory.build(team=other))

		self.assertEqual(doc.team, other)

	def test_disabled_membership_does_not_count(self):
		user = UserFactory.create_once("disabled-member@example.com").name
		enabled = BuzzTeamFactory.create_owned_by(user).name
		spare = BuzzTeamFactory.create_owned_by(UserFactory.create_once("spare-owner@example.com").name).name
		BuzzTeamMembershipFactory.create(team=spare, user=user, team_role="Manager", enabled=0)

		doc = self.insert_as(user, self.build_without_team("Event Venue", spare))

		self.assertEqual(doc.team, enabled)

	def insert_as(self, user: str, doc):
		with self.set_user(user):
			return doc.insert(ignore_permissions=True)

	def build_without_team(self, doctype: str, team: str):
		factory = TEAM_DIRECT_FACTORIES.get(doctype)
		if factory:
			doc = factory.build(team=team)
		else:
			# Event Template and Buzz Campaign have no factory yet.
			doc = frappe.get_doc(payload_for(doctype, frappe.generate_hash(length=6)))
		doc.team = None
		return doc


# Kept for the modules that still import them. Use the factories instead.
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


def create_owned_team(team_name: str, owner: str) -> str:
	team = frappe.get_doc({"doctype": "Buzz Team", "team_name": team_name})
	team.flags.owner_user = owner
	team.insert(ignore_permissions=True)
	BuzzTeamFactory.set_settings(team.name, {PAID_EVENTS_FLAG: 1})
	return team.name


def payload_for(doctype: str, suffix: str) -> dict:
	payloads = {
		"Event Venue": {"venue_name": f"Venue {suffix}", "address": "somewhere"},
		"Event Host": {"host_name": f"Host {suffix}"},
		"Event Template": {"template_name": f"Template {suffix}"},
		"Buzz Campaign": {"name": f"Campaign {suffix}", "title": suffix, "description": "why"},
		"Buzz Event": {
			"title": f"Event {suffix}",
			"category": "Test Category",
			"start_date": "2026-03-05",
			"end_date": "2026-03-06",
			"start_time": "09:00:00",
			"end_time": "18:00:00",
		},
	}
	return {"doctype": doctype, **payloads[doctype]}
