# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.desk.search import search_link
from frappe.tests import IntegrationTestCase

from buzz.api.checkin.exceptions import TicketNotFound
from buzz.api.exceptions import NotPermitted
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user, payload_for
from buzz.permissions import team_query_conditions

# Buzz Team Membership carries a team column but is scoped by its own pair of hooks.
SELF_SCOPED_DOCTYPES = frozenset({"Buzz Team Membership"})


def linked_to(doctype: str) -> set[str]:
	"""Doctypes with a Link field named after `doctype`'s short name, e.g. `team` -> Buzz Team."""
	fieldname = doctype.replace("Buzz ", "").lower()
	parents = frappe.get_all(
		"DocField",
		filters={"fieldname": fieldname, "fieldtype": "Link", "options": doctype},
		pluck="parent",
	)
	return {parent for parent in parents if not frappe.get_meta(parent).istable}


def tenant_doctypes() -> set[str]:
	"""Every doctype a team owns, derived from the schema rather than a second hardcoded list."""
	return (linked_to("Buzz Team") | linked_to("Buzz Event")) - SELF_SCOPED_DOCTYPES


def add_member(team: str, user: str, team_role: str) -> str:
	return (
		frappe.get_doc(
			{"doctype": "Buzz Team Membership", "team": team, "user": user, "team_role": team_role}
		)
		.insert(ignore_permissions=True)
		.name
	)


def create_event(title: str, team: str, is_published: int = 0) -> str:
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
				"price": 0,
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
	event: str, owner: str, attendee_email: str | None = None, booking: str | None = None
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
	frappe.db.set_value("Event Ticket", ticket.name, "owner", owner, update_modified=False)
	return ticket.name


class TeamPermissionTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

		cls.alice = create_user("perm-alice@example.com", "Alice")
		cls.bob = create_user("perm-bob@example.com", "Bob")
		cls.outsider = create_user("perm-outsider@example.com", "Outsider")

		cls.team_a = create_owned_team("Perm Team A", cls.alice)
		cls.team_b = create_owned_team("Perm Team B", cls.bob)

		cls.event_a = create_event("Perm A", cls.team_a)
		cls.event_b = create_event("Perm B", cls.team_b)

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def as_user(self, user: str):
		frappe.set_user(user)


class TestCrossTeamIsolation(TeamPermissionTestCase):
	def listed_names(self, doctype: str, **kwargs) -> list[str]:
		return frappe.get_list(doctype, pluck="name", **kwargs)

	def test_team_direct_lists_exclude_other_teams(self):
		self.as_user(self.alice)

		for doctype in linked_to("Buzz Team") - SELF_SCOPED_DOCTYPES:
			with self.subTest(doctype=doctype):
				teams = frappe.get_list(doctype, pluck="team")

				self.assertNotIn(self.team_b, teams)

	def test_event_derived_lists_exclude_other_teams(self):
		ticket_type = frappe.get_doc(
			{"doctype": "Event Ticket Type", "event": self.event_b, "title": "Hidden", "price": 0}
		).insert(ignore_permissions=True)

		self.as_user(self.alice)

		self.assertNotIn(ticket_type.name, self.listed_names("Event Ticket Type"))

	def test_team_lists_exclude_other_teams(self):
		self.as_user(self.alice)
		teams = self.listed_names("Buzz Team")

		self.assertIn(self.team_a, teams)
		self.assertNotIn(self.team_b, teams)

	def test_membership_lists_exclude_other_teams(self):
		self.as_user(self.alice)

		self.assertNotIn(self.team_b, frappe.get_list("Buzz Team Membership", pluck="team"))

	def test_every_tenant_doctype_is_wired_to_both_hooks(self):
		# Catches a new team-owned doctype that nobody registered in hooks.py.
		query_conditions = frappe.get_hooks("permission_query_conditions")
		has_permission = frappe.get_hooks("has_permission")

		for doctype in tenant_doctypes():
			with self.subTest(doctype=doctype):
				self.assertTrue(query_conditions.get(doctype))
				self.assertTrue(has_permission.get(doctype))

	def test_opening_another_teams_event_is_denied(self):
		self.as_user(self.alice)

		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Buzz Event", self.event_b).check_permission("read")

	def test_opening_another_teams_derived_doc_is_denied(self):
		ticket_type = frappe.get_doc(
			{"doctype": "Event Ticket Type", "event": self.event_b, "title": "Denied", "price": 0}
		).insert(ignore_permissions=True)

		self.as_user(self.alice)

		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Event Ticket Type", ticket_type.name).check_permission("read")

	def test_system_manager_is_unrestricted(self):
		self.assertIn(self.event_b, self.listed_names("Buzz Event"))

	def test_unstamped_rows_stay_readable_by_system_managers_only(self):
		orphan = create_event("Perm Orphan", self.team_a)
		frappe.db.set_value("Buzz Event", orphan, "team", None, update_modified=False)

		self.assertIn(orphan, self.listed_names("Buzz Event"))

		self.as_user(self.alice)

		self.assertNotIn(orphan, self.listed_names("Buzz Event"))
		# has_permission tolerates the missing team so a half-migrated site does not hard-break.
		frappe.get_doc("Buzz Event", orphan).check_permission("read")


class TestMultiTeamMembership(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.single_team_user = create_user("perm-one-team@example.com", "Single")
		add_member(cls.team_a, cls.single_team_user, "Manager")

		cls.both_teams_user = create_user("perm-both-teams@example.com", "Both")
		add_member(cls.team_a, cls.both_teams_user, "Manager")
		cls.membership_b = add_member(cls.team_b, cls.both_teams_user, "Manager")

	def listed_events(self) -> list[str]:
		return frappe.get_list("Buzz Event", pluck="name")

	def test_single_team_member_sees_their_team_and_only_their_team(self):
		self.as_user(self.single_team_user)
		events = self.listed_events()

		self.assertIn(self.event_a, events)
		self.assertNotIn(self.event_b, events)

	def test_single_team_member_writes_their_team_only(self):
		self.as_user(self.single_team_user)

		self.assertTrue(frappe.has_permission("Buzz Event", "write", doc=self.event_a))
		self.assertFalse(frappe.has_permission("Buzz Event", "write", doc=self.event_b))

	def test_member_of_both_teams_sees_both(self):
		self.as_user(self.both_teams_user)
		events = self.listed_events()

		self.assertIn(self.event_a, events)
		self.assertIn(self.event_b, events)

	def test_member_of_both_teams_writes_both(self):
		self.as_user(self.both_teams_user)

		self.assertTrue(frappe.has_permission("Buzz Event", "write", doc=self.event_a))
		self.assertTrue(frappe.has_permission("Buzz Event", "write", doc=self.event_b))

	def test_member_of_both_teams_sees_derived_rows_from_both(self):
		ours = create_ticket(self.event_a, self.alice)
		theirs = create_ticket(self.event_b, self.bob)

		self.as_user(self.both_teams_user)
		tickets = frappe.get_list("Event Ticket", pluck="name")

		self.assertIn(ours, tickets)
		self.assertIn(theirs, tickets)

	def test_disabling_one_membership_leaves_the_other_intact(self):
		membership = frappe.get_doc("Buzz Team Membership", self.membership_b)
		membership.enabled = 0
		membership.save(ignore_permissions=True)
		self.addCleanup(frappe.db.set_value, "Buzz Team Membership", self.membership_b, "enabled", 1)

		self.as_user(self.both_teams_user)
		events = self.listed_events()

		self.assertIn(self.event_a, events)
		self.assertNotIn(self.event_b, events)


class TestTeamLinkQuery(TeamPermissionTestCase):
	def searched(self, txt: str = "") -> list[str]:
		results = search_link("Buzz Team", txt, reference_doctype="Buzz Event")
		return [result["value"] for result in results]

	def test_link_search_offers_only_the_users_teams(self):
		self.as_user(self.alice)
		teams = self.searched()

		self.assertIn(self.team_a, teams)
		self.assertNotIn(self.team_b, teams)

	def test_link_search_matches_the_team_name(self):
		self.as_user(self.alice)

		self.assertEqual(self.searched("Perm Team A"), [self.team_a])
		self.assertEqual(self.searched("Perm Team B"), [])

	def test_system_manager_is_narrowed_here_despite_reading_every_team(self):
		# Administrator is on neither team, but the permission hooks let it list both.
		self.assertIn(self.team_b, frappe.get_list("Buzz Team", pluck="name"))

		self.assertNotIn(self.team_b, self.searched())

	def test_non_member_gets_nothing(self):
		self.as_user(self.outsider)

		self.assertEqual(self.searched(), [])


class TestRoleMatrix(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.viewer = create_user("perm-viewer@example.com", "Viewer")
		cls.manager = create_user("perm-manager@example.com", "Manager")
		cls.admin = create_user("perm-admin@example.com", "Admin")

		for user, team_role in ((cls.viewer, "Viewer"), (cls.manager, "Manager"), (cls.admin, "Admin")):
			add_member(cls.team_a, user, team_role)

	def can(self, user: str, ptype: str) -> bool:
		self.as_user(user)
		return frappe.has_permission("Buzz Event", ptype, doc=self.event_a)

	def test_viewer_reads_but_cannot_write(self):
		self.assertTrue(self.can(self.viewer, "read"))
		self.assertFalse(self.can(self.viewer, "write"))

	def test_manager_writes_but_cannot_delete(self):
		self.assertTrue(self.can(self.manager, "write"))
		self.assertFalse(self.can(self.manager, "delete"))

	def test_admin_deletes(self):
		self.assertTrue(self.can(self.admin, "delete"))

	def test_manager_cannot_write_another_teams_event(self):
		self.as_user(self.manager)

		self.assertFalse(frappe.has_permission("Buzz Event", "write", doc=self.event_b))


class TestNonMemberCarveOuts(TeamPermissionTestCase):
	def test_attendee_lists_own_ticket_without_a_membership(self):
		mine = create_ticket(self.event_b, self.outsider)
		theirs = create_ticket(self.event_b, self.bob)

		self.as_user(self.outsider)
		tickets = frappe.get_list("Event Ticket", pluck="name")

		self.assertIn(mine, tickets)
		self.assertNotIn(theirs, tickets)

	def test_attendee_lists_a_ticket_someone_else_created(self):
		mine = create_ticket(self.event_b, owner=self.bob, attendee_email=self.outsider)

		self.as_user(self.outsider)

		self.assertIn(mine, frappe.get_list("Event Ticket", pluck="name"))

	def test_booker_lists_a_ticket_held_by_someone_else(self):
		booking = create_booking(self.event_b, user=self.outsider)
		theirs = create_ticket(
			self.event_b, owner=self.bob, attendee_email="perm-guest@example.com", booking=booking
		)

		self.as_user(self.outsider)

		self.assertIn(theirs, frappe.get_list("Event Ticket", pluck="name"))

	def test_an_unrelated_user_sees_neither_the_ticket_nor_the_booking(self):
		booking = create_booking(self.event_b, user=self.bob)
		by_attendee = create_ticket(self.event_b, owner=self.bob, attendee_email=self.alice)
		by_booking = create_ticket(self.event_b, owner=self.bob, attendee_email=self.alice, booking=booking)

		self.as_user(self.outsider)
		tickets = frappe.get_list("Event Ticket", pluck="name")

		self.assertNotIn(by_attendee, tickets)
		self.assertNotIn(by_booking, tickets)
		self.assertNotIn(booking, frappe.get_list("Event Booking", pluck="name"))

	def test_an_unrelated_user_cannot_open_someone_elses_ticket(self):
		theirs = create_ticket(self.event_b, owner=self.bob, attendee_email=self.alice)

		self.as_user(self.outsider)

		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Event Ticket", theirs).check_permission("read")

	def test_an_unstamped_event_does_not_open_its_tickets_to_a_stranger(self):
		orphan = create_event("Perm Unstamped", self.team_b)
		theirs = create_ticket(orphan, owner=self.bob, attendee_email=self.alice)
		frappe.db.set_value("Buzz Event", orphan, "team", None, update_modified=False)

		self.as_user(self.outsider)

		self.assertNotIn(theirs, frappe.get_list("Event Ticket", pluck="name"))
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Event Ticket", theirs).check_permission("read")

	def test_attendee_reads_but_cannot_write_their_ticket(self):
		mine = create_ticket(self.event_b, owner=self.bob, attendee_email=self.outsider)

		self.as_user(self.outsider)

		self.assertTrue(frappe.has_permission("Event Ticket", "read", doc=mine))
		self.assertFalse(frappe.has_permission("Event Ticket", "write", doc=mine))

	def test_buyer_lists_a_guest_checkout_booking(self):
		# Guest checkout runs as Administrator, so `owner` never names the buyer.
		booking = create_booking(self.event_b, user=self.outsider, owner="Administrator")

		self.as_user(self.outsider)

		self.assertIn(booking, frappe.get_list("Event Booking", pluck="name"))

	def test_buyer_reads_their_own_booking_but_writes_nothing(self):
		# Bookings are only ever written by the service flow and by organisers. The
		# portal reads them; transfers and cancellations go through their own doctypes.
		mine = create_booking(self.event_b, user=self.outsider, owner="Administrator")
		theirs = create_booking(self.event_b, user=self.bob)

		self.as_user(self.outsider)

		self.assertTrue(frappe.has_permission("Event Booking", "read", doc=mine))
		self.assertFalse(frappe.has_permission("Event Booking", "write", doc=mine))
		self.assertFalse(frappe.has_permission("Event Booking", "write", doc=theirs))

	def test_nobody_deletes_a_booking_from_the_portal(self):
		# Bookings are cancelled, never deleted — the role carries no delete at all, so this
		# holds for the buyer's own row as much as for a stranger's.
		mine = create_booking(self.event_b, user=self.outsider)
		guest_checkout = create_booking(self.event_b, user=self.outsider, owner="Guest")
		theirs = create_booking(self.event_b, user=self.bob)

		self.as_user(self.outsider)

		for booking in (mine, guest_checkout, theirs):
			self.assertFalse(frappe.has_permission("Event Booking", "delete", doc=booking))
			with self.assertRaises(frappe.PermissionError):
				frappe.delete_doc("Event Booking", booking)

	def test_attendee_gets_no_carve_out_on_payments(self):
		self.as_user(self.outsider)

		with self.assertRaises(frappe.PermissionError):
			frappe.get_list("Event Payment", pluck="name")

	def test_published_sponsorship_tier_is_visible_to_non_members(self):
		published = create_event("Perm Published", self.team_b, is_published=1)
		visible = frappe.get_doc(
			{"doctype": "Sponsorship Tier", "event": published, "title": "Gold", "amount": 1}
		).insert(ignore_permissions=True)
		hidden = frappe.get_doc(
			{"doctype": "Sponsorship Tier", "event": self.event_b, "title": "Silver", "amount": 1}
		).insert(ignore_permissions=True)

		self.as_user(self.outsider)
		tiers = frappe.get_list("Sponsorship Tier", pluck="name")

		self.assertIn(visible.name, tiers)
		self.assertNotIn(hidden.name, tiers)

	def test_published_events_stay_visible_to_non_members(self):
		published = create_event("Perm Public", self.team_b, is_published=1)

		self.as_user(self.outsider)

		self.assertIn(published, frappe.get_list("Buzz Event", pluck="name"))
		self.assertNotIn(self.event_b, frappe.get_list("Buzz Event", pluck="name"))

	def test_guest_event_reads_are_never_narrowed(self):
		self.assertIsNone(team_query_conditions(user="Guest", doctype="Buzz Event"))


class TestTeamSettingsPermissions(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = create_user("perm-settings-manager@example.com", "Manager")
		add_member(cls.team_a, cls.manager, "Manager")
		cls.admin = create_user("perm-settings-admin@example.com", "Admin")
		add_member(cls.team_a, cls.admin, "Admin")

	def can(self, user: str, ptype: str) -> bool:
		self.as_user(user)
		return frappe.has_permission("Buzz Team Settings", ptype, doc=self.team_a)

	def test_manager_reads_but_cannot_write(self):
		self.assertTrue(self.can(self.manager, "read"))
		self.assertFalse(self.can(self.manager, "write"))

	def test_admin_writes(self):
		self.assertTrue(self.can(self.admin, "write"))

	def test_non_member_is_refused(self):
		self.assertFalse(self.can(self.outsider, "read"))

	def test_another_teams_settings_are_not_listed(self):
		self.as_user(self.alice)

		self.assertNotIn(self.team_b, frappe.get_list("Buzz Team Settings", pluck="team"))


class TestTalkProposalComposition(TeamPermissionTestCase):
	def create_proposal(self, event: str, submitted_by: str) -> str:
		proposal = frappe.get_doc(
			{
				"doctype": "Talk Proposal",
				"event": event,
				"title": f"Proposal {frappe.generate_hash(length=6)}",
				"submitted_by": submitted_by,
				"status": frappe.db.get_value("Talk Proposal Status", {}, "name"),
				"speakers": [{"first_name": "Speaker", "email": submitted_by}],
			}
		)
		return proposal.insert(ignore_permissions=True).name

	def test_speaker_sees_own_proposal_without_a_membership(self):
		mine = self.create_proposal(self.event_b, self.outsider)

		self.as_user(self.outsider)

		self.assertIn(mine, frappe.get_list("Talk Proposal", pluck="name"))

	def test_team_member_sees_their_teams_proposals_only(self):
		ours = self.create_proposal(self.event_a, self.outsider)
		theirs = self.create_proposal(self.event_b, self.outsider)

		self.as_user(self.alice)
		proposals = frappe.get_list("Talk Proposal", pluck="name")

		self.assertIn(ours, proposals)
		self.assertNotIn(theirs, proposals)


class TestCheckinIsolation(TeamPermissionTestCase):
	def test_frontdesk_cannot_check_in_another_teams_ticket(self):
		from buzz.api.checkin import validate_ticket_for_checkin

		frontdesk = create_user("perm-frontdesk@example.com", "Frontdesk")
		add_member(self.team_a, frontdesk, "Frontdesk")

		ticket_type = frappe.get_doc(
			{"doctype": "Event Ticket Type", "event": self.event_b, "title": "Scan", "price": 0}
		).insert(ignore_permissions=True)
		ticket = frappe.get_doc(
			{
				"doctype": "Event Ticket",
				"event": self.event_b,
				"ticket_type": ticket_type.name,
				"attendee_name": "Other Team",
				"attendee_email": "other-team@example.com",
			}
		).insert(ignore_permissions=True)

		self.as_user(frontdesk)

		with self.assertRaises(NotPermitted):
			validate_ticket_for_checkin(ticket.name)

	def test_unknown_ticket_still_raises_not_found(self):
		from buzz.api.checkin import validate_ticket_for_checkin

		frontdesk = create_user("perm-frontdesk-2@example.com", "Frontdesk")
		add_member(self.team_a, frontdesk, "Frontdesk")

		self.as_user(frontdesk)

		with self.assertRaises(TicketNotFound):
			validate_ticket_for_checkin("no-such-ticket")
