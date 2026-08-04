# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team.test_buzz_team import create_user, payload_for
from buzz.patches.assign_default_team import execute as backfill_teams
from buzz.patches.create_default_teams import execute as create_default_teams
from buzz.patches.create_default_teams import get_enabled_event_managers


class TestCreateDefaultTeams(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		# The patch reads the whole site, so a manager belonging to the database — or to the
		# previous test — would decide who owns this test's team.
		for user in get_enabled_event_managers():
			self.retire(user)

	def create_manager(self, email: str, first_name: str) -> str:
		user = create_user(email, first_name)
		frappe.get_doc("User", user).add_roles("Event Manager")
		return user

	@staticmethod
	def retire(user: str) -> None:
		frappe.get_doc("User", user).remove_roles("Event Manager")

	def create_event_owned_by(self, user: str, suffix: str) -> str:
		event = frappe.get_doc(payload_for("Buzz Event", suffix))
		event.flags.ignore_mandatory = True
		event.insert(ignore_permissions=True)
		frappe.db.set_value("Buzz Event", event.name, "owner", user, update_modified=False)
		return event.name

	def team_of(self, user: str) -> str | None:
		return frappe.db.get_value("Buzz Team Membership", {"user": user, "enabled": 1}, "team")

	def role_in(self, team: str, user: str) -> str | None:
		return frappe.db.get_value(
			"Buzz Team Membership", {"team": team, "user": user, "enabled": 1}, "team_role"
		)

	def test_every_manager_lands_in_one_shared_team(self):
		owner = self.create_manager("shared-owner@example.com", "Owner")
		other = self.create_manager("shared-other@example.com", "Other")
		self.create_event_owned_by(owner, "Shared")

		create_default_teams()

		team = self.team_of(owner)
		self.assertEqual(self.role_in(team, owner), "Owner")
		self.assertEqual(self.role_in(team, other), "Admin")

	def test_owner_is_the_manager_who_created_the_most_events(self):
		quiet = self.create_manager("top-quiet@example.com", "Quiet")
		busy = self.create_manager("top-busy@example.com", "Busy")
		self.create_event_owned_by(quiet, "Quiet One")
		self.create_event_owned_by(busy, "Busy One")
		self.create_event_owned_by(busy, "Busy Two")

		create_default_teams()

		team = self.team_of(busy)
		self.assertEqual(self.role_in(team, busy), "Owner")
		self.assertEqual(self.role_in(team, quiet), "Admin")

	def test_an_equal_event_count_goes_to_the_earlier_manager(self):
		first = self.create_manager("tie-first@example.com", "First")
		second = self.create_manager("tie-second@example.com", "Second")
		self.create_event_owned_by(second, "Tie One")
		self.create_event_owned_by(first, "Tie Two")

		create_default_teams()

		team = self.team_of(first)
		self.assertEqual(self.role_in(team, first), "Owner")
		self.assertEqual(self.role_in(team, second), "Admin")

	def test_a_site_without_events_falls_back_to_the_earlier_manager(self):
		first = self.create_manager("no-events-first@example.com", "First")
		second = self.create_manager("no-events-second@example.com", "Second")

		create_default_teams()

		team = self.team_of(first)
		self.assertEqual(self.role_in(team, first), "Owner")
		self.assertEqual(self.role_in(team, second), "Admin")

	def test_a_disabled_manager_gets_no_membership(self):
		active = self.create_manager("lapsed-active@example.com", "Active")
		lapsed = self.create_manager("lapsed-manager@example.com", "Lapsed")
		frappe.db.set_value("User", lapsed, "enabled", 0)
		self.addCleanup(frappe.db.set_value, "User", lapsed, "enabled", 1)

		create_default_teams()

		self.assertIsNotNone(self.team_of(active))
		self.assertIsNone(self.team_of(lapsed))

	def test_administrator_neither_owns_nor_joins_the_team(self):
		frappe.get_doc("User", "Administrator").add_roles("Event Manager")
		self.addCleanup(self.retire, "Administrator")
		manager = self.create_manager("admin-excluded@example.com", "Excluded")
		colleague = self.create_manager("admin-excluded-peer@example.com", "Peer")
		self.create_event_owned_by("Administrator", "Administrator's Own")

		create_default_teams()

		team = self.team_of(manager)
		self.assertEqual(self.role_in(team, manager), "Owner")
		self.assertEqual(self.role_in(team, colleague), "Admin")
		self.assertIsNone(self.role_in(team, "Administrator"))

	def test_a_site_without_managers_gets_no_team(self):
		teams = frappe.db.count("Buzz Team")

		create_default_teams()

		self.assertEqual(frappe.db.count("Buzz Team"), teams)

	def test_a_rerun_adds_no_team_and_demotes_no_one(self):
		owner = self.create_manager("rerun-owner@example.com", "Owner")
		other = self.create_manager("rerun-other@example.com", "Other")
		self.create_event_owned_by(owner, "Rerun")

		create_default_teams()
		teams = frappe.db.count("Buzz Team")
		memberships = frappe.db.count("Buzz Team Membership")
		create_default_teams()

		self.assertEqual(frappe.db.count("Buzz Team"), teams)
		self.assertEqual(frappe.db.count("Buzz Team Membership"), memberships)
		self.assertEqual(self.role_in(self.team_of(owner), owner), "Owner")
		self.assertEqual(self.role_in(self.team_of(other), other), "Admin")


class TestAssignDefaultTeam(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def create_teamless_venue(self, name: str) -> str:
		venue = frappe.get_doc(payload_for("Event Venue", name)).insert(ignore_permissions=True)
		frappe.db.set_value("Event Venue", venue.name, "team", None, update_modified=False)
		return venue.name

	def test_backfills_teamless_rows_and_is_idempotent(self):
		venue = self.create_teamless_venue("Legacy")

		backfill_teams()
		assigned = frappe.db.get_value("Event Venue", venue, "team")

		self.assertTrue(assigned)

		backfill_teams()

		self.assertEqual(frappe.db.get_value("Event Venue", venue, "team"), assigned)

	def test_a_site_without_teamless_rows_gets_no_fallback_team(self):
		teams = frappe.db.count("Buzz Team")

		backfill_teams()

		self.assertEqual(frappe.db.count("Buzz Team"), teams)
