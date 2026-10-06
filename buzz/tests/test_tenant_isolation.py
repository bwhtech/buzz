import frappe
from frappe.desk.search import search_link

from buzz.api.checkin import validate_ticket_for_checkin
from buzz.api.checkin.exceptions import TicketNotFound
from buzz.api.exceptions import NotPermitted
from buzz.permissions import team_query_conditions
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamMembershipFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
	SponsorshipTierFactory,
	TalkProposalFactory,
	UserFactory,
)

# Buzz Team Membership carries a team column but is scoped by its own pair of hooks.
SELF_SCOPED_DOCTYPES = frozenset({"Buzz Team Membership"})


class TestCrossTeamIsolation(TeamPermissionTestCase):
	def test_team_direct_lists_exclude_other_teams(self):
		for doctype in linked_to("Buzz Team") - SELF_SCOPED_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertNotIn(self.team_b, self.list_as(self.alice, doctype, pluck="team"))

	def test_event_derived_lists_exclude_other_teams(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event_b)

		self.assertNotIn(ticket_type.name, self.list_as(self.alice, "Event Ticket Type"))

	def test_team_lists_exclude_other_teams(self):
		teams = self.list_as(self.alice, "Buzz Team")

		self.assertIn(self.team_a, teams)
		self.assertNotIn(self.team_b, teams)

	def test_membership_lists_exclude_other_teams(self):
		self.assertNotIn(self.team_b, self.list_as(self.alice, "Buzz Team Membership", pluck="team"))

	def test_every_tenant_doctype_is_wired_to_both_hooks(self):
		# Catches a new team-owned doctype that nobody registered in hooks.py.
		query_conditions = frappe.get_hooks("permission_query_conditions")
		has_permission = frappe.get_hooks("has_permission")

		for doctype in tenant_doctypes():
			with self.subTest(doctype=doctype):
				self.assertTrue(query_conditions.get(doctype))
				self.assertTrue(has_permission.get(doctype))

	def test_every_query_condition_is_valid_sql(self):
		# Hook output is stringified into the WHERE clause, so pypika's ANSI quoting would reach MariaDB.
		hooks = frappe.get_hooks("permission_query_conditions", app_name="buzz")

		for doctype, methods in hooks.items():
			for method in methods:
				with self.subTest(doctype=doctype):
					condition = frappe.call(frappe.get_attr(method), self.alice, doctype=doctype)
					self.assertIsInstance(condition, str)
					frappe.db.sql(f"SELECT `name` FROM `tab{doctype}` WHERE {condition} LIMIT 1")

	def test_opening_another_teams_event_is_denied(self):
		with self.set_user(self.alice), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Buzz Event", self.event_b).check_permission("read")

	def test_opening_another_teams_derived_doc_is_denied(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event_b)

		with self.set_user(self.alice), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Event Ticket Type", ticket_type.name).check_permission("read")

	def test_system_manager_is_unrestricted(self):
		self.assertIn(self.event_b, frappe.get_list("Buzz Event", pluck="name"))

	def test_unstamped_rows_stay_readable_by_system_managers_only(self):
		orphan = BuzzEventFactory.create("unpublished", team=self.team_a).name
		frappe.db.set_value("Buzz Event", orphan, "team", None, update_modified=False)

		self.assertIn(orphan, frappe.get_list("Buzz Event", pluck="name"))
		self.assertNotIn(orphan, self.list_as(self.alice, "Buzz Event"))
		# has_permission tolerates the missing team so a half-migrated site does not hard-break.
		with self.set_user(self.alice):
			frappe.get_doc("Buzz Event", orphan).check_permission("read")


class TestPublicVisibility(TeamPermissionTestCase):
	def test_published_events_stay_visible_to_non_members(self):
		published = BuzzEventFactory.create(team=self.team_b).name

		events = self.list_as(self.outsider, "Buzz Event")

		self.assertIn(published, events)
		self.assertNotIn(self.event_b, events)

	def test_published_sponsorship_tier_is_visible_to_non_members(self):
		published = BuzzEventFactory.create(team=self.team_b).name
		visible = SponsorshipTierFactory.create(event=published).name
		hidden = SponsorshipTierFactory.create(event=self.event_b).name

		tiers = self.list_as(self.outsider, "Sponsorship Tier")

		self.assertIn(visible, tiers)
		self.assertNotIn(hidden, tiers)

	def test_guest_event_reads_are_never_narrowed(self):
		self.assertIsNone(team_query_conditions(user="Guest", doctype="Buzz Event"))

	def test_attendee_gets_no_carve_out_on_payments(self):
		with self.set_user(self.outsider), self.assertRaises(frappe.PermissionError):
			frappe.get_list("Event Payment", pluck="name")


class TestTeamLinkQuery(TeamPermissionTestCase):
	def test_link_search_offers_only_the_users_teams(self):
		teams = self.search_teams_as(self.alice)

		self.assertIn(self.team_a, teams)
		self.assertNotIn(self.team_b, teams)

	def test_link_search_matches_the_team_name(self):
		self.assertEqual(self.search_teams_as(self.alice, "Perm Team A"), [self.team_a])
		self.assertEqual(self.search_teams_as(self.alice, "Perm Team B"), [])

	def test_system_manager_is_narrowed_here_despite_reading_every_team(self):
		# Administrator is on neither team, but the permission hooks let it list both.
		self.assertIn(self.team_b, frappe.get_list("Buzz Team", pluck="name"))

		self.assertNotIn(self.team_b, self.search_teams_as("Administrator"))

	def test_non_member_gets_nothing(self):
		self.assertEqual(self.search_teams_as(self.outsider), [])

	def search_teams_as(self, user: str, txt: str = "") -> list[str]:
		with self.set_user(user):
			results = search_link("Buzz Team", txt, reference_doctype="Buzz Event")
		return [result["value"] for result in results]


class TestTalkProposalComposition(TeamPermissionTestCase):
	def test_speaker_sees_own_proposal_without_a_membership(self):
		mine = self.create_proposal(self.event_b)

		self.assertIn(mine, self.list_as(self.outsider, "Talk Proposal"))

	def test_team_member_sees_their_teams_proposals_only(self):
		ours = self.create_proposal(self.event_a)
		theirs = self.create_proposal(self.event_b)

		proposals = self.list_as(self.alice, "Talk Proposal")

		self.assertIn(ours, proposals)
		self.assertNotIn(theirs, proposals)

	def create_proposal(self, event: str) -> str:
		return TalkProposalFactory.create(event=event, submitted_by=self.outsider).name


class TestCheckinIsolation(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.frontdesk = UserFactory.create_once("perm-frontdesk@example.com").name
		BuzzTeamMembershipFactory.create(team=cls.team_a, user=cls.frontdesk, team_role="Frontdesk")

	def test_frontdesk_cannot_check_in_another_teams_ticket(self):
		ticket = EventTicketFactory.create(event=self.event_b).name

		with self.set_user(self.frontdesk), self.assertRaises(NotPermitted):
			validate_ticket_for_checkin(ticket)

	def test_unknown_ticket_still_raises_not_found(self):
		with self.set_user(self.frontdesk), self.assertRaises(TicketNotFound):
			validate_ticket_for_checkin("no-such-ticket")


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
	"""Derived from the schema, so a new team-owned doctype cannot be missed."""
	return (linked_to("Buzz Team") | linked_to("Buzz Event")) - SELF_SCOPED_DOCTYPES
