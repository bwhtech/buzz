import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventBookingFactory,
	EventTicketFactory,
	UserFactory,
)


class TicketAccessTestCase(IntegrationTestCase):
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

	def setUp(self):
		self.enterContext(self.set_user("Administrator"))

	def list_as(self, user: str, doctype: str = "Event Ticket") -> list[str]:
		with self.set_user(user):
			return frappe.get_list(doctype, pluck="name")

	def has_permission_as(self, user: str, ptype: str, doctype: str, doc: str) -> bool:
		with self.set_user(user):
			return frappe.has_permission(doctype, ptype, doc=doc)

	def create_ticket(self, owner: str, *traits: str, **overrides) -> str:
		"""On event B, held by `owner` unless `attendee_email` says otherwise."""
		ticket = EventTicketFactory.create(
			*traits, **{"event": self.event_b, "attendee_email": owner, **overrides}
		)
		frappe.db.set_value("Event Ticket", ticket.name, "owner", owner, update_modified=False)
		return ticket.name

	def create_booking(self, user: str, owner: str | None = None) -> str:
		booking = EventBookingFactory.create(event=self.event_b, user=user)
		frappe.db.set_value("Event Booking", booking.name, "owner", owner or user, update_modified=False)
		return booking.name


class TestNonMemberCarveOuts(TicketAccessTestCase):
	def test_attendee_lists_own_ticket_without_a_membership(self):
		mine = self.create_ticket(self.outsider)
		theirs = self.create_ticket(self.bob)

		tickets = self.list_as(self.outsider)

		self.assertIn(mine, tickets)
		self.assertNotIn(theirs, tickets)

	def test_attendee_lists_a_ticket_someone_else_created(self):
		mine = self.create_ticket(self.bob, attendee_email=self.outsider)

		self.assertIn(mine, self.list_as(self.outsider))

	def test_booker_lists_a_ticket_held_by_someone_else(self):
		booking = self.create_booking(self.outsider)
		theirs = self.create_ticket(self.bob, attendee_email="perm-guest@example.com", booking=booking)

		self.assertIn(theirs, self.list_as(self.outsider))

	def test_an_unrelated_user_sees_neither_the_ticket_nor_the_booking(self):
		booking = self.create_booking(self.bob)
		by_attendee = self.create_ticket(self.bob, attendee_email=self.alice)
		by_booking = self.create_ticket(self.bob, attendee_email=self.alice, booking=booking)

		tickets = self.list_as(self.outsider)

		self.assertNotIn(by_attendee, tickets)
		self.assertNotIn(by_booking, tickets)
		self.assertNotIn(booking, self.list_as(self.outsider, "Event Booking"))

	def test_an_unrelated_user_cannot_open_someone_elses_ticket(self):
		theirs = self.create_ticket(self.bob, attendee_email=self.alice)

		with self.set_user(self.outsider), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Event Ticket", theirs).check_permission("read")

	def test_an_unstamped_event_does_not_open_its_tickets_to_a_stranger(self):
		orphan = BuzzEventFactory.create("unpublished", team=self.team_b).name
		theirs = self.create_ticket(self.bob, event=orphan, attendee_email=self.alice)
		frappe.db.set_value("Buzz Event", orphan, "team", None, update_modified=False)

		self.assertNotIn(theirs, self.list_as(self.outsider))
		with self.set_user(self.outsider), self.assertRaises(frappe.PermissionError):
			frappe.get_doc("Event Ticket", theirs).check_permission("read")

	def test_attendee_reads_but_cannot_write_their_ticket(self):
		mine = self.create_ticket(self.bob, attendee_email=self.outsider)

		self.assertTrue(self.has_permission_as(self.outsider, "read", "Event Ticket", mine))
		self.assertFalse(self.has_permission_as(self.outsider, "write", "Event Ticket", mine))

	def test_buyer_lists_a_guest_checkout_booking(self):
		# Guest checkout runs as Administrator, so `owner` never names the buyer.
		booking = self.create_booking(self.outsider, owner="Administrator")

		self.assertIn(booking, self.list_as(self.outsider, "Event Booking"))

	def test_buyer_reads_their_own_booking_but_writes_nothing(self):
		# Only the service flow and organisers write bookings; the portal only reads them.
		mine = self.create_booking(self.outsider, owner="Administrator")
		theirs = self.create_booking(self.bob)

		self.assertTrue(self.has_permission_as(self.outsider, "read", "Event Booking", mine))
		self.assertFalse(self.has_permission_as(self.outsider, "write", "Event Booking", mine))
		self.assertFalse(self.has_permission_as(self.outsider, "write", "Event Booking", theirs))

	def test_nobody_deletes_a_booking_from_the_portal(self):
		# Bookings are cancelled, never deleted, so even the buyer has no delete.
		mine = self.create_booking(self.outsider)
		guest_checkout = self.create_booking(self.outsider, owner="Guest")
		theirs = self.create_booking(self.bob)

		for booking in (mine, guest_checkout, theirs):
			with self.subTest(booking=booking):
				self.assertFalse(self.has_permission_as(self.outsider, "delete", "Event Booking", booking))
				with self.set_user(self.outsider), self.assertRaises(frappe.PermissionError):
					frappe.delete_doc("Event Booking", booking)


class TicketHolderTestCase(TicketAccessTestCase):
	"""A ticket is owned by whoever booked it, which is rarely the attendee holding it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.booker = UserFactory.create_once("perm-booker@example.com").name
		cls.holder = UserFactory.create_once("perm-holder@example.com").name
		cls.stranger = UserFactory.create_once("perm-stranger@example.com").name
		cls.viewer = UserFactory.create_once("perm-viewer@example.com").name
		BuzzTeamMembershipFactory.create(team=cls.team_b, user=cls.viewer, team_role="Viewer")

	def create_held_ticket(self, owner: str | None = None) -> str:
		return self.create_ticket(owner or self.booker, "submitted", attendee_email=self.holder)


class TestTicketHolderVisibility(TicketHolderTestCase):
	def test_holder_sees_a_guest_booked_ticket(self):
		ticket = self.create_held_ticket(owner="Guest")

		self.assertIn(ticket, self.list_as(self.holder))

	def test_booker_still_sees_the_tickets_they_created(self):
		ticket = self.create_held_ticket()

		self.assertIn(ticket, self.list_as(self.booker))

	def test_team_member_reads_every_ticket_for_their_event(self):
		ticket = self.create_held_ticket()

		self.assertTrue(self.has_permission_as(self.bob, "read", "Event Ticket", ticket))

	def test_viewer_sees_their_teams_tickets(self):
		ticket = self.create_held_ticket()

		self.assertIn(ticket, self.list_as(self.viewer))


class TestTicketImmutability(TicketHolderTestCase):
	"""Reading a ticket you hold is a carve-out. Changing one is not."""

	def test_holder_cannot_cancel_or_delete_their_ticket(self):
		ticket = self.create_held_ticket()

		self.assertFalse(self.has_permission_as(self.holder, "cancel", "Event Ticket", ticket))
		self.assertFalse(self.has_permission_as(self.holder, "delete", "Event Ticket", ticket))

	def test_holder_saving_their_ticket_is_refused(self):
		ticket = self.create_ticket(self.booker, attendee_email=self.holder)

		with self.set_user(self.holder):
			doc = frappe.get_doc("Event Ticket", ticket)
			doc.attendee_name = "Renamed"

			with self.assertRaises(frappe.PermissionError):
				doc.save()

	def test_stranger_cannot_write_another_persons_ticket(self):
		ticket = self.create_held_ticket()

		self.assertFalse(self.has_permission_as(self.stranger, "write", "Event Ticket", ticket))

	def test_submitted_ticket_is_frozen_even_for_administrator(self):
		doc = frappe.get_doc("Event Ticket", self.create_held_ticket())
		doc.event = self.event_a

		with self.assertRaises(frappe.UpdateAfterSubmitError):
			doc.save()

	def test_only_the_transfer_fields_stay_editable_after_submit(self):
		editable = {
			field.fieldname for field in frappe.get_meta("Event Ticket").fields if field.allow_on_submit
		}

		# The ticket transfer flow needs these four and nothing else.
		self.assertEqual(editable, {"first_name", "last_name", "attendee_name", "attendee_email"})
