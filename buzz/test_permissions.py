# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventTicketFactory,
	UserFactory,
)


class RoleTestCase(IntegrationTestCase):
	"""Alice owns team A, Bob owns team B, and each team has one unpublished event."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.alice = UserFactory.create_once("perm-alice@example.com").name
		cls.bob = UserFactory.create_once("perm-bob@example.com").name
		cls.outsider = UserFactory.create_once("perm-outsider@example.com").name
		cls.team_a = BuzzTeamFactory.create_owned_by(cls.alice).name
		cls.team_b = BuzzTeamFactory.create_owned_by(cls.bob).name
		cls.event_a = BuzzEventFactory.create("unpublished", team=cls.team_a).name
		cls.event_b = BuzzEventFactory.create("unpublished", team=cls.team_b).name

	@classmethod
	def add_members(cls, team: str, *members: tuple[str, str]) -> list[str]:
		return [
			BuzzTeamMembershipFactory.create(
				team=team, user=UserFactory.create_once(email).name, team_role=team_role
			).name
			for email, team_role in members
		]

	def setUp(self):
		self.enterContext(self.set_user("Administrator"))

	def has_permission_as(self, user: str, ptype: str, doctype: str, doc: str) -> bool:
		with self.set_user(user):
			return frappe.has_permission(doctype, ptype, doc=doc)

	def list_as(self, user: str, doctype: str, pluck: str = "name") -> list:
		with self.set_user(user):
			return frappe.get_list(doctype, pluck=pluck)


class TestRoleMatrix(RoleTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.viewer, cls.manager, cls.admin = (
			"perm-viewer@example.com",
			"perm-manager@example.com",
			"perm-admin@example.com",
		)
		cls.add_members(cls.team_a, (cls.viewer, "Viewer"), (cls.manager, "Manager"), (cls.admin, "Admin"))

	def test_viewer_reads_but_cannot_write(self):
		self.assertTrue(self.has_event_permission(self.viewer, "read"))
		self.assertFalse(self.has_event_permission(self.viewer, "write"))

	def test_manager_writes_but_cannot_delete(self):
		self.assertTrue(self.has_event_permission(self.manager, "write"))
		self.assertFalse(self.has_event_permission(self.manager, "delete"))

	def test_admin_deletes(self):
		self.assertTrue(self.has_event_permission(self.admin, "delete"))

	def test_manager_cannot_write_another_teams_event(self):
		self.assertFalse(self.has_permission_as(self.manager, "write", "Buzz Event", self.event_b))

	def has_event_permission(self, user: str, ptype: str) -> bool:
		return self.has_permission_as(user, ptype, "Buzz Event", self.event_a)


class TestTeamSettingsPermissions(RoleTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager, cls.admin = "perm-settings-manager@example.com", "perm-settings-admin@example.com"
		cls.add_members(cls.team_a, (cls.manager, "Manager"), (cls.admin, "Admin"))

	def test_manager_reads_but_cannot_write(self):
		self.assertTrue(self.has_settings_permission(self.manager, "read"))
		self.assertFalse(self.has_settings_permission(self.manager, "write"))

	def test_admin_writes(self):
		self.assertTrue(self.has_settings_permission(self.admin, "write"))

	def test_non_member_is_refused(self):
		self.assertFalse(self.has_settings_permission(self.outsider, "read"))

	def test_another_teams_settings_are_not_listed(self):
		self.assertNotIn(self.team_b, self.list_as(self.alice, "Buzz Team Settings", pluck="team"))

	def has_settings_permission(self, user: str, ptype: str) -> bool:
		return self.has_permission_as(user, ptype, "Buzz Team Settings", self.team_a)


class TestMultiTeamMembership(RoleTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.single_team_user = "perm-one-team@example.com"
		cls.both_teams_user = "perm-both-teams@example.com"
		cls.add_members(cls.team_a, (cls.single_team_user, "Manager"), (cls.both_teams_user, "Manager"))
		[cls.membership_b] = cls.add_members(cls.team_b, (cls.both_teams_user, "Manager"))

	def test_single_team_member_sees_their_team_and_only_their_team(self):
		events = self.list_as(self.single_team_user, "Buzz Event")

		self.assertIn(self.event_a, events)
		self.assertNotIn(self.event_b, events)

	def test_single_team_member_writes_their_team_only(self):
		self.assertTrue(self.has_permission_as(self.single_team_user, "write", "Buzz Event", self.event_a))
		self.assertFalse(self.has_permission_as(self.single_team_user, "write", "Buzz Event", self.event_b))

	def test_member_of_both_teams_sees_both(self):
		events = self.list_as(self.both_teams_user, "Buzz Event")

		self.assertIn(self.event_a, events)
		self.assertIn(self.event_b, events)

	def test_member_of_both_teams_writes_both(self):
		self.assertTrue(self.has_permission_as(self.both_teams_user, "write", "Buzz Event", self.event_a))
		self.assertTrue(self.has_permission_as(self.both_teams_user, "write", "Buzz Event", self.event_b))

	def test_member_of_both_teams_sees_derived_rows_from_both(self):
		ours = EventTicketFactory.create(event=self.event_a).name
		theirs = EventTicketFactory.create(event=self.event_b).name

		tickets = self.list_as(self.both_teams_user, "Event Ticket")

		self.assertIn(ours, tickets)
		self.assertIn(theirs, tickets)

	def test_disabling_one_membership_leaves_the_other_intact(self):
		membership = frappe.get_doc("Buzz Team Membership", self.membership_b)
		membership.enabled = 0
		membership.save()
		self.addCleanup(frappe.db.set_value, "Buzz Team Membership", self.membership_b, "enabled", 1)

		events = self.list_as(self.both_teams_user, "Buzz Event")

		self.assertIn(self.event_a, events)
		self.assertNotIn(self.event_b, events)
