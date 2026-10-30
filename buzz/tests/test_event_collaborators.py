# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe

from buzz.api.checkin.services import checkin_events, ensure_can_check_in
from buzz.api.events import get_event, get_my_events
from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.exceptions import NotPermitted
from buzz.api.teams import get_my_teams
from buzz.permissions import (
	DOCTYPE_SECTION,
	SECTIONS,
	derived_has_permission,
	get_section_access,
	has_section_permission,
)
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	AdditionalEventPageFactory,
	BuzzEventCollaboratorFactory,
	BuzzEventFactory,
	BuzzTeamMembershipFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
	SponsorshipTierFactory,
	TalkProposalFactory,
	UserFactory,
)
from buzz.tests.utils import SELF_SCOPED_DOCTYPES, linked_to

# One real row per section; the other doctypes are covered through their permission hook.
SAMPLE_DOCTYPE = {
	"details": "Additional Event Page",
	"guests": "Event Ticket",
	"ticketing": "Event Ticket Type",
	"talks": "Talk Proposal",
	"sponsors": "Sponsorship Tier",
}
SAMPLE_FACTORY = {
	"details": AdditionalEventPageFactory,
	"guests": EventTicketFactory,
	"ticketing": EventTicketTypeFactory,
	"talks": TalkProposalFactory,
	"sponsors": SponsorshipTierFactory,
}


class CollaboratorTestCase(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.events = (cls.event_a, cls.event_a2, cls.event_b)
		cls.collaborators = {section: cls.collaborator_for(section) for section in SECTIONS}
		cls.rows = {
			section: {event: factory.create(event=event).name for event in cls.events}
			for section, factory in SAMPLE_FACTORY.items()
		}

	@classmethod
	def collaborator_for(cls, section: str, event: str | None = None, level: str = "Edit") -> str:
		email = f"collab-{section}-{level.lower()}@example.com"
		access = {"details_access": level} | ({f"{section}_access": level} if section != "details" else {})
		BuzzEventCollaboratorFactory.create("accepted", event=event or cls.event_a, email=email, **access)
		return email

	def list_names(self, user: str, doctype: str) -> set:
		return set(self.list_as(user, doctype))


class TestSectionWiring(CollaboratorTestCase):
	def test_every_derived_doctype_has_a_section(self):
		hooks = frappe.get_hooks("permission_query_conditions", app_name="buzz")
		derived = {doctype for doctype, methods in hooks.items() if "derived_query_conditions" in methods[0]}

		# A Buzz Form takes its section from the doctype it collects.
		self.assertEqual(derived - set(DOCTYPE_SECTION) - {"Buzz Form"}, set())

	def test_every_section_is_mapped(self):
		self.assertEqual(set(DOCTYPE_SECTION.values()), set(SECTIONS))


class TestSectionIsolation(CollaboratorTestCase):
	def test_collaborator_lists_only_their_section_on_their_event(self):
		for section, sample in SAMPLE_DOCTYPE.items():
			with self.subTest(section=section):
				listed = self.list_names(self.collaborators[section], sample)

				self.assertIn(self.rows[section][self.event_a], listed)
				self.assertNotIn(self.rows[section][self.event_a2], listed)
				self.assertNotIn(self.rows[section][self.event_b], listed)

	def test_collaborator_lists_nothing_from_other_sections(self):
		for section, user in self.collaborators.items():
			for other, sample in SAMPLE_DOCTYPE.items():
				if other in (section, "details"):
					continue
				with self.subTest(section=section, other=other):
					self.assertEqual(self.list_names(user, sample) & set(self.rows[other].values()), set())

	def test_collaborator_reads_no_other_section_by_permission_hook(self):
		for section, user in self.collaborators.items():
			for doctype, doctype_section in DOCTYPE_SECTION.items():
				doc = frappe.get_doc({"doctype": doctype, "event": self.event_a})
				with self.subTest(section=section, doctype=doctype):
					allowed = doctype_section in (section, "details") and doctype != "Talk Proposal"
					if doctype != "Talk Proposal":
						self.assertEqual(derived_has_permission(doc, "read", user), allowed)

	def test_collaborator_gets_no_other_event_of_the_team(self):
		for section, user in self.collaborators.items():
			doc = frappe.get_doc({"doctype": "Event Ticket Type", "event": self.event_a2})
			with self.subTest(section=section):
				self.assertFalse(derived_has_permission(doc, "read", user))
				self.assertFalse(has_section_permission(self.event_a2, "details", "read", user))

	def test_team_level_doctypes_stay_hidden(self):
		user = self.collaborators["guests"]
		for doctype in linked_to("Buzz Team") - SELF_SCOPED_DOCTYPES - {"Buzz Event"}:
			# Rows with no team, such as the standard schedule item types, are shared by design.
			with self.subTest(doctype=doctype), self.set_user(user):
				self.assertEqual(frappe.get_list(doctype, filters={"team": ["is", "set"]}, pluck="name"), [])

	def test_team_member_lists_are_unchanged(self):
		listed = self.list_names(self.alice, "Event Ticket Type")

		self.assertLessEqual(
			{self.rows["ticketing"][self.event_a], self.rows["ticketing"][self.event_a2]}, listed
		)
		self.assertNotIn(self.rows["ticketing"][self.event_b], listed)


class TestCollaboratorStatus(CollaboratorTestCase):
	def test_pending_and_revoked_rows_give_no_access(self):
		user = UserFactory.create_once("pending@example.com").name
		row = BuzzEventCollaboratorFactory.create(
			"pending", event=self.event_a, email=user, user=user, guests_access="View"
		)
		self.assertEqual(set(get_section_access(user, self.event_a).values()), {None})

		frappe.db.set_value("Buzz Event Collaborator", row.name, "status", "Revoked")
		self.assertEqual(set(get_section_access(user, self.event_a).values()), {None})

	def test_revoking_removes_frappe_roles(self):
		email = self.collaborators["guests"]
		self.assertIn("Frontdesk Manager", frappe.get_roles(email))
		self.assertIn("Event Manager", frappe.get_roles(email))

		row = frappe.get_doc("Buzz Event Collaborator", {"email": email})
		row.status = "Revoked"
		row.save()

		self.assertNotIn("Event Manager", frappe.get_roles(email))
		self.assertNotIn("Frontdesk Manager", frappe.get_roles(email))

	def test_revoking_keeps_roles_a_membership_earns(self):
		email = "collab-and-member@example.com"
		user = UserFactory.create_once(email).name
		BuzzTeamMembershipFactory.create(team=self.team_b, user=user, team_role="Manager")
		row = BuzzEventCollaboratorFactory.create(
			"accepted", event=self.event_a, email=email, guests_access="Edit"
		)

		row.status = "Revoked"
		row.save()

		self.assertIn("Event Manager", frappe.get_roles(email))

	def test_view_only_collaborator_earns_no_managed_role(self):
		email = self.collaborator_for("guests", level="View")

		self.assertNotIn("Event Manager", frappe.get_roles(email))
		self.assertNotIn("Frontdesk Manager", frappe.get_roles(email))


class TestCollaboratorRows(CollaboratorTestCase):
	def test_collaborator_cannot_list_other_collaborators(self):
		self.assertEqual(self.list_names(self.collaborators["guests"], "Buzz Event Collaborator"), set())

	def test_outsider_lists_nothing(self):
		with self.assertRaises(frappe.PermissionError):
			self.list_names(self.outsider, "Buzz Event Collaborator")
		self.assertEqual(self.list_names(self.outsider, "Event Ticket Type"), set())

	def test_team_member_lists_their_events_collaborators_only(self):
		BuzzEventCollaboratorFactory.create(
			"accepted", event=self.event_b, email="collab-b@example.com", guests_access="View"
		)

		rows = frappe.get_list("Buzz Event Collaborator", pluck="email")
		with self.set_user(self.alice):
			rows = frappe.get_list("Buzz Event Collaborator", pluck="email")

		self.assertIn(self.collaborators["guests"], rows)
		self.assertNotIn("collab-b@example.com", rows)

	def test_collaborator_has_no_team(self):
		with self.set_user(self.collaborators["guests"]):
			self.assertEqual(get_my_teams(), [])

	def test_collaborator_sees_only_their_event(self):
		with self.set_user(self.collaborators["guests"]):
			response = get_my_events()

		names = {str(event.name) for event in response.upcoming + response.past}
		self.assertEqual(names, {str(self.event_a)})


class TestAccessLevels(CollaboratorTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.viewer = cls.collaborator_for("guests", level="View")
		cls.editor = cls.collaborators["guests"]

	def test_view_reads_but_cannot_write(self):
		self.assertTrue(has_section_permission(self.event_a, "guests", "read", self.viewer))
		self.assertFalse(has_section_permission(self.event_a, "guests", "write", self.viewer))

	def test_view_section_write_is_refused_on_the_document(self):
		ticket = self.rows["guests"][self.event_a]

		self.assertTrue(self.has_permission_as(self.viewer, "read", "Event Ticket", ticket))
		self.assertFalse(self.has_permission_as(self.viewer, "write", "Event Ticket", ticket))

	def test_edit_writes_on_the_granted_event_only(self):
		self.assertTrue(
			self.has_permission_as(self.editor, "write", "Event Ticket", self.rows["guests"][self.event_a])
		)
		self.assertFalse(
			self.has_permission_as(self.editor, "write", "Event Ticket", self.rows["guests"][self.event_a2])
		)

	def test_edit_never_deletes(self):
		for section, user in self.collaborators.items():
			with self.subTest(section=section):
				self.assertFalse(has_section_permission(self.event_a, section, "delete", user))

	def test_edit_in_one_section_is_not_edit_in_another(self):
		self.assertFalse(has_section_permission(self.event_a, "ticketing", "write", self.editor))
		self.assertTrue(has_section_permission(self.event_a, "details", "write", self.editor))

	def test_details_view_opens_the_event_read_only(self):
		with self.set_user(self.viewer):
			self.assertFalse(get_event(str(self.event_a)).can_write)
			with self.assertRaises(CannotManageEvent):
				get_event(str(self.event_a2))

	def test_details_edit_opens_the_event_writable(self):
		with self.set_user(self.editor):
			self.assertTrue(get_event(str(self.event_a)).can_write)

	def test_details_view_lists_the_events_extra_pages_only(self):
		listed = self.list_names(self.viewer, "Additional Event Page")

		self.assertIn(self.rows["details"][self.event_a], listed)
		self.assertNotIn(self.rows["details"][self.event_a2], listed)

	def test_event_write_follows_details_level(self):
		self.assertTrue(self.has_permission_as(self.editor, "write", "Buzz Event", self.event_a))
		self.assertFalse(self.has_permission_as(self.viewer, "write", "Buzz Event", self.event_a))
		self.assertFalse(self.has_permission_as(self.editor, "write", "Buzz Event", self.event_a2))
		self.assertFalse(self.has_permission_as(self.editor, "delete", "Buzz Event", self.event_a))


class TestTeamSectionAccess(CollaboratorTestCase):
	def test_team_roles_map_to_levels(self):
		expectations = {
			"Owner": {section: "Edit" for section in SECTIONS},
			"Manager": {section: "Edit" for section in SECTIONS},
			"Frontdesk": {section: "Edit" if section == "guests" else "View" for section in SECTIONS},
			"Viewer": {section: "View" for section in SECTIONS},
		}
		for team_role, expected in expectations.items():
			user = UserFactory.create_once(f"section-{team_role.lower()}@example.com").name
			BuzzTeamMembershipFactory.create(team=self.team_a, user=user, team_role=team_role)
			with self.subTest(team_role=team_role):
				self.assertEqual(get_section_access(user, self.event_a), expected)

	def test_outsider_has_no_access(self):
		self.assertEqual(set(get_section_access(self.outsider, self.event_a).values()), {None})

	def test_other_teams_member_has_no_access(self):
		self.assertEqual(set(get_section_access(self.bob, self.event_a).values()), {None})


class TestCollaboratorCheckin(CollaboratorTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.live_event = BuzzEventFactory.create(team=cls.team_a).name
		cls.other_live_event = BuzzEventFactory.create(team=cls.team_a).name
		cls.frontdesk = cls.collaborator_for("guests", event=cls.live_event)
		cls.viewer = cls.collaborator_for("guests", event=cls.live_event, level="View")

	def test_guests_edit_checks_in_on_their_event_only(self):
		with self.set_user(self.frontdesk):
			ensure_can_check_in(self.live_event)
			with self.assertRaises(NotPermitted):
				ensure_can_check_in(self.other_live_event)

	def test_guests_view_cannot_check_in(self):
		with self.set_user(self.viewer), self.assertRaises(NotPermitted):
			ensure_can_check_in(self.live_event)

	def test_checkin_events_lists_the_collaborators_event_only(self):
		with self.set_user(self.frontdesk):
			names = {str(event.name) for event in checkin_events()}

		self.assertEqual(names, {str(self.live_event)})

	def test_other_sections_edit_cannot_check_in(self):
		user = self.collaborators["ticketing"]
		with self.set_user(user), self.assertRaises(NotPermitted):
			ensure_can_check_in(self.event_a)
