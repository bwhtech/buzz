# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.desk.query_report import run as run_report

from buzz.api.events import get_event_ticket_types, set_registration_state, update_tax_settings
from buzz.api.exceptions import BuzzAPIError
from buzz.events.report.event_attendance_summary import event_attendance_summary
from buzz.events.report.event_overview import event_overview
from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import (
	AttendeeTicketAddOnFactory,
	BuzzEventCollaboratorFactory,
	EventBookingFactory,
	EventBookingRefundFactory,
	EventPaymentFactory,
	SpeakerProfileFactory,
	TicketCancellationRequestFactory,
	UserFactory,
)
from buzz.ticketing.report.detailed_event_registrations import detailed_event_registrations
from buzz.ticketing.report.event_add_ons_overview import event_add_ons_overview

BUZZ_ROLES = ("Event Manager", "Frontdesk Manager", "Buzz User")

# Readable by every Buzz role on purpose: lookup lists and public speaker bios.
PUBLIC_DOCTYPES = frozenset(
	{"Buzz Theme", "Event Category", "Event Topic", "Talk Proposal Status", "Speaker Profile"}
)

BOOKING_LINKED_DOCTYPES = (
	"Event Payment",
	"Ticket Cancellation Request",
	"Event Booking Refund",
	"Attendee Ticket Add-on",
)

REPORTS = {
	"Event Overview": event_overview.execute,
	"Event Attendance Summary": event_attendance_summary.execute,
	"Detailed Event Registrations": detailed_event_registrations.execute,
	"Event Add-Ons Overview": event_add_ons_overview.execute,
}


def collaborator(event: str, email: str, **sections) -> str:
	BuzzEventCollaboratorFactory.create(
		"accepted", event=event, email=email, details_access="View", **sections
	)
	return email


class LeakTestCase(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.guests_viewer = collaborator(cls.event_a, "leak-guests@example.com", guests_access="View")
		cls.guests_editor = collaborator(cls.event_a, "leak-guests-edit@example.com", guests_access="Edit")
		# Edit earns Event Manager, the role every unhooked doctype would fall open to.
		cls.ticketing_editor = collaborator(
			cls.event_a, "leak-ticketing@example.com", ticketing_access="Edit"
		)
		cls.attendee = UserFactory.create_once("leak-attendee@example.com").name
		cls.records = {
			event: cls.booking_records(event) for event in (cls.event_a, cls.event_a2, cls.event_b)
		}

	@classmethod
	def booking_records(cls, event: str) -> dict[str, str]:
		add_on = AttendeeTicketAddOnFactory.create().name
		booking = EventBookingFactory.create(event=event, user=cls.attendee)
		booking.attendees[0].db_set("add_ons", add_on)
		return {
			"Event Booking": booking.name,
			"Event Payment": EventPaymentFactory.create(
				reference_doctype="Event Booking", reference_docname=booking.name, user=cls.attendee
			).name,
			"Ticket Cancellation Request": TicketCancellationRequestFactory.create(booking=booking.name).name,
			"Event Booking Refund": EventBookingRefundFactory.create(booking=booking.name, amount=1).name,
			"Attendee Ticket Add-on": add_on,
		}

	def names(self, event: str, doctype: str) -> str:
		return self.records[event][doctype]


class TestRoleReachableDoctypes(LeakTestCase):
	def test_every_doctype_a_buzz_role_reads_is_row_scoped_or_public(self):
		query_hooks = frappe.get_hooks("permission_query_conditions")
		doc_hooks = frappe.get_hooks("has_permission")

		for doctype in doctypes_readable_by(BUZZ_ROLES) - PUBLIC_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertTrue(query_hooks.get(doctype), "no permission_query_conditions hook")
				self.assertTrue(doc_hooks.get(doctype), "no has_permission hook")


class TestBookingLinkedDoctypes(LeakTestCase):
	def test_guests_editor_lists_only_their_events_rows(self):
		for doctype in BOOKING_LINKED_DOCTYPES:
			with self.subTest(doctype=doctype):
				listed = set(self.list_as(self.guests_editor, doctype))

				self.assertIn(self.names(self.event_a, doctype), listed)
				self.assertNotIn(self.names(self.event_a2, doctype), listed)
				self.assertNotIn(self.names(self.event_b, doctype), listed)

	def test_collaborator_without_guests_lists_none(self):
		for doctype in BOOKING_LINKED_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertEqual(self.list_as(self.ticketing_editor, doctype), [])

	def test_another_teams_manager_lists_none(self):
		for doctype in BOOKING_LINKED_DOCTYPES:
			with self.subTest(doctype=doctype):
				listed = set(self.list_as(self.bob, doctype))

				self.assertNotIn(self.names(self.event_a, doctype), listed)
				self.assertIn(self.names(self.event_b, doctype), listed)

	def test_document_reads_follow_the_guests_section(self):
		for doctype in BOOKING_LINKED_DOCTYPES:
			with self.subTest(doctype=doctype):
				own, sibling = self.names(self.event_a, doctype), self.names(self.event_a2, doctype)

				self.assertTrue(self.has_permission_as(self.guests_editor, "read", doctype, own))
				self.assertFalse(self.has_permission_as(self.guests_editor, "read", doctype, sibling))
				# Like a team Viewer, a View collaborator holds no role that reads these at all.
				self.assertFalse(self.has_permission_as(self.guests_viewer, "read", doctype, own))
				self.assertFalse(self.has_permission_as(self.ticketing_editor, "read", doctype, own))
				self.assertFalse(self.has_permission_as(self.outsider, "read", doctype, own))

	def test_guests_view_cannot_write(self):
		payment = self.names(self.event_a, "Event Payment")

		self.assertFalse(self.has_permission_as(self.guests_viewer, "write", "Event Payment", payment))


class TestReports(LeakTestCase):
	def test_reports_refuse_an_event_outside_the_users_guests_access(self):
		for report, execute in REPORTS.items():
			for user, event in (
				(self.alice, self.event_b),
				(self.guests_viewer, self.event_a2),
				(self.ticketing_editor, self.event_a),
				(self.attendee, self.event_b),
			):
				with self.subTest(report=report, user=user, event=event):
					with self.set_user(user), self.assertRaises(frappe.PermissionError):
						execute(frappe._dict(event=event))

	def test_reports_run_for_the_users_own_event(self):
		for report, execute in REPORTS.items():
			for user in (self.alice, self.guests_viewer):
				with self.subTest(report=report, user=user), self.set_user(user):
					execute(frappe._dict(event=self.event_a))

	def test_overview_without_an_event_lists_only_readable_events(self):
		with self.set_user(self.alice):
			_columns, rows = event_overview.execute(frappe._dict())

		events = {row["event"] for row in rows}
		self.assertLessEqual({self.event_a, self.event_a2}, events)
		self.assertNotIn(self.event_b, events)

	def test_report_route_refuses_another_teams_event(self):
		with self.set_user(self.alice), self.assertRaises(frappe.PermissionError):
			run_report("Detailed Event Registrations", filters={"event": self.event_b})


class TestSpeakerProfile(LeakTestCase):
	def test_event_managers_cannot_edit_someone_elses_profile(self):
		speaker = UserFactory.create_once("leak-speaker@example.com").name
		profile = SpeakerProfileFactory.create(user=speaker).name

		self.assertFalse(self.has_permission_as(self.alice, "write", "Speaker Profile", profile))
		self.assertFalse(self.has_permission_as(self.ticketing_editor, "delete", "Speaker Profile", profile))
		self.assertTrue(self.has_permission_as(self.ticketing_editor, "read", "Speaker Profile", profile))


class TestTicketingPayload(LeakTestCase):
	def setUp(self):
		super().setUp()
		frappe.db.set_value("Buzz Team Settings", self.team_a, {"legal_name": "Team A Pvt", "tax_id": "TAXA"})

	def test_collaborator_does_not_get_the_teams_tax_details(self):
		with self.set_user(self.ticketing_editor):
			payload = get_event_ticket_types(str(self.event_a))

		self.assertIsNone(payload.team_legal_name)
		self.assertIsNone(payload.team_tax_id)
		self.assertTrue(payload.has_team_tax_details)

	def test_team_member_gets_the_teams_tax_details(self):
		with self.set_user(self.alice):
			payload = get_event_ticket_types(str(self.event_a))

		self.assertEqual(payload.team_tax_id, "TAXA")


class TestRegistrationPageWrites(LeakTestCase):
	def test_ticketing_edit_closes_registrations_and_sets_tax(self):
		with self.set_user(self.ticketing_editor):
			self.assertTrue(set_registration_state(str(self.event_a), True).registrations_closed)
			update_tax_settings(str(self.event_a), False, False, "GST", 18)

	def test_ticketing_edit_is_refused_on_another_event(self):
		with self.set_user(self.ticketing_editor), self.assertRaises(BuzzAPIError):
			set_registration_state(str(self.event_a2), True)

	def test_guests_view_cannot_close_registrations(self):
		with self.set_user(self.guests_viewer), self.assertRaises(BuzzAPIError):
			set_registration_state(str(self.event_a), True)


class TestCollaboratorNeedsASection(LeakTestCase):
	def test_details_view_alone_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			BuzzEventCollaboratorFactory.create(event=self.event_a, email="leak-empty@example.com")

	def test_details_edit_alone_is_allowed(self):
		BuzzEventCollaboratorFactory.create(
			event=self.event_a, email="leak-details@example.com", details_access="Edit"
		)


def doctypes_readable_by(roles: tuple[str, ...]) -> set[str]:
	"""Buzz doctypes any of `roles` can read, through standard or custom role permissions."""
	readable = set()
	for perm_doctype in ("DocPerm", "Custom DocPerm"):
		readable |= set(
			frappe.get_all(perm_doctype, filters={"role": ("in", roles), "read": 1}, pluck="parent")
		)
	buzz_modules = set(frappe.get_all("Module Def", filters={"app_name": "buzz"}, pluck="name"))
	return {
		doctype
		for doctype in readable
		if frappe.db.get_value("DocType", doctype, "module") in buzz_modules
		and not frappe.get_meta(doctype).istable
	}
