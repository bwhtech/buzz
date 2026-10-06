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
		"""Each member is `(email, team_role)`; returns the membership names."""
		return [
			BuzzTeamMembershipFactory.create(
				team=team, user=UserFactory.create_once(email).name, team_role=team_role
			).name
			for email, team_role in members
		]

	def setUp(self):
		self.enterContext(self.set_user("Administrator"))

	def can(self, user: str, ptype: str, doctype: str, doc: str) -> bool:
		with self.set_user(user):
			return frappe.has_permission(doctype, ptype, doc=doc)

	def listed(self, user: str, doctype: str, pluck: str = "name") -> list:
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
		self.assertTrue(self.can_on_event_a(self.viewer, "read"))
		self.assertFalse(self.can_on_event_a(self.viewer, "write"))

	def test_manager_writes_but_cannot_delete(self):
		self.assertTrue(self.can_on_event_a(self.manager, "write"))
		self.assertFalse(self.can_on_event_a(self.manager, "delete"))

	def test_admin_deletes(self):
		self.assertTrue(self.can_on_event_a(self.admin, "delete"))

	def test_manager_cannot_write_another_teams_event(self):
		self.assertFalse(self.can(self.manager, "write", "Buzz Event", self.event_b))

	def can_on_event_a(self, user: str, ptype: str) -> bool:
		return self.can(user, ptype, "Buzz Event", self.event_a)


class TestTeamSettingsPermissions(RoleTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager, cls.admin = "perm-settings-manager@example.com", "perm-settings-admin@example.com"
		cls.add_members(cls.team_a, (cls.manager, "Manager"), (cls.admin, "Admin"))

	def test_manager_reads_but_cannot_write(self):
		self.assertTrue(self.can_on_settings(self.manager, "read"))
		self.assertFalse(self.can_on_settings(self.manager, "write"))

	def test_admin_writes(self):
		self.assertTrue(self.can_on_settings(self.admin, "write"))

	def test_non_member_is_refused(self):
		self.assertFalse(self.can_on_settings(self.outsider, "read"))

	def test_another_teams_settings_are_not_listed(self):
		self.assertNotIn(self.team_b, self.listed(self.alice, "Buzz Team Settings", pluck="team"))

	def can_on_settings(self, user: str, ptype: str) -> bool:
		return self.can(user, ptype, "Buzz Team Settings", self.team_a)


class TestMultiTeamMembership(RoleTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.single_team_user = "perm-one-team@example.com"
		cls.both_teams_user = "perm-both-teams@example.com"
		cls.add_members(cls.team_a, (cls.single_team_user, "Manager"), (cls.both_teams_user, "Manager"))
		[cls.membership_b] = cls.add_members(cls.team_b, (cls.both_teams_user, "Manager"))

	def test_single_team_member_sees_their_team_and_only_their_team(self):
		events = self.listed(self.single_team_user, "Buzz Event")

		self.assertIn(self.event_a, events)
		self.assertNotIn(self.event_b, events)

	def test_single_team_member_writes_their_team_only(self):
		self.assertTrue(self.can(self.single_team_user, "write", "Buzz Event", self.event_a))
		self.assertFalse(self.can(self.single_team_user, "write", "Buzz Event", self.event_b))

	def test_member_of_both_teams_sees_both(self):
		events = self.listed(self.both_teams_user, "Buzz Event")

		self.assertIn(self.event_a, events)
		self.assertIn(self.event_b, events)

	def test_member_of_both_teams_writes_both(self):
		self.assertTrue(self.can(self.both_teams_user, "write", "Buzz Event", self.event_a))
		self.assertTrue(self.can(self.both_teams_user, "write", "Buzz Event", self.event_b))

	def test_member_of_both_teams_sees_derived_rows_from_both(self):
		ours = EventTicketFactory.create(event=self.event_a).name
		theirs = EventTicketFactory.create(event=self.event_b).name

		tickets = self.listed(self.both_teams_user, "Event Ticket")

		self.assertIn(ours, tickets)
		self.assertIn(theirs, tickets)

	def test_disabling_one_membership_leaves_the_other_intact(self):
		membership = frappe.get_doc("Buzz Team Membership", self.membership_b)
		membership.enabled = 0
		membership.save()
		self.addCleanup(frappe.db.set_value, "Buzz Team Membership", self.membership_b, "enabled", 1)

		events = self.listed(self.both_teams_user, "Buzz Event")

		self.assertIn(self.event_a, events)
		self.assertNotIn(self.event_b, events)


# Kept for the modules that still import them. Use the factories instead.
def add_member(team: str, user: str, team_role: str) -> str:
	return (
		frappe.get_doc(
			{"doctype": "Buzz Team Membership", "team": team, "user": user, "team_role": team_role}
		)
		.insert(ignore_permissions=True)
		.name
	)


def create_event(title: str, team: str, is_published: int = 0) -> str:
	from buzz.events.doctype.buzz_team.test_buzz_team import payload_for

	payload = payload_for("Buzz Event", title)
	return (
		frappe.get_doc({**payload, "team": team, "is_published": is_published})
		.insert(ignore_permissions=True)
		.name
	)


def create_ticket_type(event: str) -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": event,
				"title": f"Type {frappe.generate_hash(length=6)}",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def create_booking(event: str, user: str, owner: str | None = None) -> str:
	# Event Booking.validate prices the attendee rows, so it needs at least one.
	booking = frappe.get_doc(
		{
			"doctype": "Event Booking",
			"event": event,
			"user": user,
			"attendees": [
				{"ticket_type": create_ticket_type(event), "first_name": "Attendee", "email": user}
			],
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value("Event Booking", booking.name, "owner", owner or user, update_modified=False)
	return booking.name


def create_ticket(
	event: str,
	owner: str,
	attendee_email: str | None = None,
	booking: str | None = None,
	submit: bool = False,
) -> str:
	ticket = frappe.get_doc(
		{
			"doctype": "Event Ticket",
			"event": event,
			"ticket_type": create_ticket_type(event),
			"attendee_name": "Attendee",
			"attendee_email": attendee_email or owner,
			"booking": booking,
		}
	).insert(ignore_permissions=True)
	if submit:
		ticket.submit()
	frappe.db.set_value("Event Ticket", ticket.name, "owner", owner, update_modified=False)
	return ticket.name
