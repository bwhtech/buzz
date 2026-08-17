# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.forms.test_forms import ensure_prompt_named_record
from buzz.proposals.doctype.talk_proposal.test_talk_proposal import make_test_user

ATTENDEE = "perm-attendee@example.com"
BUYER = "perm-buyer@example.com"
OUTSIDER = "perm-outsider@example.com"


def create_event() -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": f"Perm Event {frappe.generate_hash(length=6)}",
				"start_date": "2030-01-01",
				"end_date": "2030-01-01",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"category": ensure_prompt_named_record("Event Category", "Perm Category"),
				"host": ensure_prompt_named_record("Event Host", "Perm Host"),
				"is_published": 1,
			}
		)
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


class TestOwnedPermissions(IntegrationTestCase):
	"""Bookings and tickets belong to the person they name, not to whoever created the row."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = create_event()
		for email in (ATTENDEE, BUYER, OUTSIDER):
			make_test_user(email)

	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")

	def as_user(self, user: str):
		frappe.set_user(user)

	def test_attendee_lists_a_ticket_someone_else_created(self):
		mine = create_ticket(self.event, owner=BUYER, attendee_email=ATTENDEE)

		self.as_user(ATTENDEE)

		self.assertIn(mine, frappe.get_list("Event Ticket", pluck="name"))

	def test_booker_lists_a_ticket_held_by_someone_else(self):
		booking = create_booking(self.event, user=BUYER)
		theirs = create_ticket(
			self.event, owner="Administrator", attendee_email="perm-guest@example.com", booking=booking
		)

		self.as_user(BUYER)

		self.assertIn(theirs, frappe.get_list("Event Ticket", pluck="name"))

	def test_an_unrelated_user_sees_neither_the_ticket_nor_the_booking(self):
		booking = create_booking(self.event, user=BUYER)
		by_attendee = create_ticket(self.event, owner=BUYER, attendee_email=ATTENDEE)
		by_booking = create_ticket(self.event, owner=BUYER, attendee_email=ATTENDEE, booking=booking)

		self.as_user(OUTSIDER)
		tickets = frappe.get_list("Event Ticket", pluck="name")

		self.assertNotIn(by_attendee, tickets)
		self.assertNotIn(by_booking, tickets)
		self.assertNotIn(booking, frappe.get_list("Event Booking", pluck="name"))

	def test_an_unrelated_user_cannot_open_someone_elses_ticket(self):
		theirs = create_ticket(self.event, owner=BUYER, attendee_email=ATTENDEE)

		self.as_user(OUTSIDER)

		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Event Ticket", theirs).check_permission("read")

	def test_attendee_reads_but_cannot_write_their_ticket(self):
		mine = create_ticket(self.event, owner=BUYER, attendee_email=ATTENDEE)

		self.as_user(ATTENDEE)

		self.assertTrue(frappe.has_permission("Event Ticket", "read", doc=mine))
		self.assertFalse(frappe.has_permission("Event Ticket", "write", doc=mine))

	def test_buyer_lists_a_guest_checkout_booking(self):
		# Guest checkout runs as Administrator, so `owner` never names the buyer.
		booking = create_booking(self.event, user=BUYER, owner="Administrator")

		self.as_user(BUYER)

		self.assertIn(booking, frappe.get_list("Event Booking", pluck="name"))

	def test_buyer_writes_their_own_booking_but_nobody_elses(self):
		mine = create_booking(self.event, user=BUYER, owner="Administrator")
		theirs = create_booking(self.event, user=ATTENDEE)

		self.as_user(BUYER)

		self.assertTrue(frappe.has_permission("Event Booking", "write", doc=mine))
		self.assertFalse(frappe.has_permission("Event Booking", "write", doc=theirs))

	def test_nobody_deletes_a_booking_from_the_portal(self):
		# Bookings are cancelled, never deleted — the role carries no delete at all, so this
		# holds for the buyer's own row as much as for a stranger's.
		mine = create_booking(self.event, user=BUYER)
		guest_checkout = create_booking(self.event, user=BUYER, owner="Guest")
		theirs = create_booking(self.event, user=ATTENDEE)

		self.as_user(BUYER)

		for booking in (mine, guest_checkout, theirs):
			self.assertFalse(frappe.has_permission("Event Booking", "delete", doc=booking))
			with self.assertRaises(frappe.PermissionError):
				frappe.delete_doc("Event Booking", booking)

	def test_an_event_manager_still_reads_every_row(self):
		manager = make_test_user("perm-manager@example.com", roles=["Event Manager"])
		theirs = create_ticket(self.event, owner=BUYER, attendee_email=ATTENDEE)

		self.as_user(manager)

		self.assertIn(theirs, frappe.get_list("Event Ticket", pluck="name"))
		self.assertTrue(frappe.has_permission("Event Ticket", "read", doc=theirs))
