# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.install import create_administrator_team
from buzz.patches.assign_default_team import execute as backfill_teams
from buzz.patches.create_default_teams import execute as create_default_teams
from buzz.patches.create_default_teams import get_enabled_event_managers
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, EventVenueFactory, UserFactory


class TestCreateDefaultTeams(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Built before setUp retires every manager, so the team owner it adds does not count.
		cls.team = BuzzTeamFactory.create_owned_by().name

	def setUp(self):
		# The patch reads every manager on the site, so earlier ones would pick the owner.
		for user in get_enabled_event_managers():
			self.remove_event_manager_role(user)

	def test_every_manager_lands_in_one_shared_team(self):
		owner = self.create_manager("shared-owner@example.com")
		other = self.create_manager("shared-other@example.com")
		self.create_event_owned_by(owner)

		create_default_teams()

		team = self.team_of(owner)
		self.assertEqual(self.role_in(team, owner), "Owner")
		self.assertEqual(self.role_in(team, other), "Admin")

	def test_owner_is_the_manager_who_created_the_most_events(self):
		quiet = self.create_manager("top-quiet@example.com")
		busy = self.create_manager("top-busy@example.com")
		self.create_event_owned_by(quiet)
		self.create_event_owned_by(busy)
		self.create_event_owned_by(busy)

		create_default_teams()

		team = self.team_of(busy)
		self.assertEqual(self.role_in(team, busy), "Owner")
		self.assertEqual(self.role_in(team, quiet), "Admin")

	def test_an_equal_event_count_goes_to_the_earlier_manager(self):
		first = self.create_manager("tie-first@example.com")
		second = self.create_manager("tie-second@example.com")
		self.create_event_owned_by(second)
		self.create_event_owned_by(first)

		create_default_teams()

		team = self.team_of(first)
		self.assertEqual(self.role_in(team, first), "Owner")
		self.assertEqual(self.role_in(team, second), "Admin")

	def test_a_site_without_events_falls_back_to_the_earlier_manager(self):
		first = self.create_manager("no-events-first@example.com")
		second = self.create_manager("no-events-second@example.com")

		create_default_teams()

		team = self.team_of(first)
		self.assertEqual(self.role_in(team, first), "Owner")
		self.assertEqual(self.role_in(team, second), "Admin")

	def test_a_disabled_manager_gets_no_membership(self):
		active = self.create_manager("lapsed-active@example.com")
		lapsed = self.create_manager("lapsed-manager@example.com")
		frappe.db.set_value("User", lapsed, "enabled", 0)
		self.addCleanup(frappe.db.set_value, "User", lapsed, "enabled", 1)

		create_default_teams()

		self.assertIsNotNone(self.team_of(active))
		self.assertIsNone(self.team_of(lapsed))

	def test_administrator_neither_owns_nor_joins_the_team(self):
		frappe.get_doc("User", "Administrator").add_roles("Event Manager")
		self.addCleanup(self.remove_event_manager_role, "Administrator")
		manager = self.create_manager("admin-excluded@example.com")
		colleague = self.create_manager("admin-excluded-peer@example.com")
		self.create_event_owned_by("Administrator")

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
		owner = self.create_manager("rerun-owner@example.com")
		other = self.create_manager("rerun-other@example.com")
		self.create_event_owned_by(owner)

		create_default_teams()
		teams = frappe.db.count("Buzz Team")
		memberships = frappe.db.count("Buzz Team Membership")
		create_default_teams()

		self.assertEqual(frappe.db.count("Buzz Team"), teams)
		self.assertEqual(frappe.db.count("Buzz Team Membership"), memberships)
		self.assertEqual(self.role_in(self.team_of(owner), owner), "Owner")
		self.assertEqual(self.role_in(self.team_of(other), other), "Admin")

	def create_manager(self, email: str) -> str:
		user = UserFactory.create_once(email)
		user.add_roles("Event Manager")
		return user.name

	@staticmethod
	def remove_event_manager_role(user: str) -> None:
		frappe.get_doc("User", user).remove_roles("Event Manager")

	def create_event_owned_by(self, user: str) -> str:
		event = BuzzEventFactory.create(team=self.team)
		frappe.db.set_value("Buzz Event", event.name, "owner", user, update_modified=False)
		return event.name

	def team_of(self, user: str) -> str | None:
		return frappe.db.get_value("Buzz Team Membership", {"user": user, "enabled": 1}, "team")

	def role_in(self, team: str, user: str) -> str | None:
		return frappe.db.get_value(
			"Buzz Team Membership", {"team": team, "user": user, "enabled": 1}, "team_role"
		)


class TestAssignDefaultTeam(IntegrationTestCase):
	def test_backfills_teamless_rows_and_is_idempotent(self):
		venue = self.create_teamless_venue()

		backfill_teams()
		assigned = frappe.db.get_value("Event Venue", venue, "team")

		self.assertTrue(assigned)

		backfill_teams()

		self.assertEqual(frappe.db.get_value("Event Venue", venue, "team"), assigned)

	def test_a_site_without_teamless_rows_gets_no_fallback_team(self):
		teams = frappe.db.count("Buzz Team")

		backfill_teams()

		self.assertEqual(frappe.db.count("Buzz Team"), teams)

	def create_teamless_venue(self) -> str:
		venue = EventVenueFactory.create()
		frappe.db.set_value("Event Venue", venue.name, "team", None, update_modified=False)
		return venue.name


class TestCreateAdministratorTeam(IntegrationTestCase):
	def test_a_site_without_teams_gets_one_owned_by_administrator(self):
		self.clear_teams()

		create_administrator_team()

		self.assertTrue(self.administrator_team())
		self.assertEqual(frappe.db.count("Buzz Team"), 1)

	def test_a_site_with_teams_gets_no_new_team(self):
		self.clear_teams()
		BuzzTeamFactory.create_owned_by()
		teams = frappe.db.count("Buzz Team")

		create_administrator_team()

		self.assertEqual(frappe.db.count("Buzz Team"), teams)
		self.assertIsNone(self.administrator_team())

	def clear_teams(self):
		frappe.db.savepoint("before_clearing_teams")
		self.addCleanup(frappe.db.rollback, save_point="before_clearing_teams")
		for doctype in ("Buzz Team Membership", "Buzz Team Settings", "Buzz Team"):
			frappe.db.delete(doctype)

	def administrator_team(self) -> str | None:
		return frappe.db.get_value(
			"Buzz Team Membership", {"user": "Administrator", "team_role": "Owner"}, "team"
		)
