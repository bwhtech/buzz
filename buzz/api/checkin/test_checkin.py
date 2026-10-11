import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.checkin import (
	checkin_ticket,
	get_checkin_events,
	get_checkin_guests,
	validate_ticket_for_checkin,
)
from buzz.api.checkin.exceptions import AlreadyCheckedIn, TicketCancelled, TicketNotFound
from buzz.api.exceptions import NotPermitted
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventBookingFactory,
	EventPaymentFactory,
	EventTicketFactory,
	UserFactory,
)


class CheckinTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create().name

	def setUp(self):
		frappe.clear_messages()
		self.ticket = EventTicketFactory.create(event=self.event).name

	def create_paid_ticket(self, amount: int) -> str:
		booking = EventBookingFactory.create(event=self.event, payment_status="Paid")
		booking.submit()
		EventPaymentFactory.create(
			"received",
			reference_doctype="Event Booking",
			reference_docname=booking.name,
			amount=amount,
			currency=booking.currency,
		)
		return frappe.db.get_value("Event Ticket", {"booking": booking.name}, "name")


class TestValidateTicketForCheckin(CheckinTestCase):
	def test_unknown_ticket_raises_not_found(self):
		with self.assertRaises(TicketNotFound):
			validate_ticket_for_checkin("no-such-ticket")

		self.assertEqual(frappe.local.message_log[-1]["title"], "Ticket Not Found")

	def test_ticket_reads_as_not_checked_in(self):
		ticket = validate_ticket_for_checkin(self.ticket).__json__()["ticket"]

		self.assertEqual(ticket["id"], self.ticket)
		self.assertFalse(ticket["is_checked_in"])
		self.assertIsNone(ticket["check_in_time"])
		self.assertIsNone(ticket["check_in_date"])

	def test_payment_details_are_reported_for_a_paid_booking(self):
		ticket = self.create_paid_ticket(amount=250)

		response = validate_ticket_for_checkin(ticket).__json__()

		self.assertEqual(response["payment_details"]["amount"], 250)

	def test_cancelled_ticket_is_rejected(self):
		frappe.db.set_value("Event Ticket", self.ticket, "docstatus", 2)
		frappe.clear_document_cache("Event Ticket", self.ticket)

		with self.assertRaises(TicketCancelled):
			validate_ticket_for_checkin(self.ticket)


class TestCheckinTicket(CheckinTestCase):
	def test_checkin_records_and_reports(self):
		response = checkin_ticket(self.ticket).__json__()

		self.assertTrue(response["ticket"]["is_checked_in"])
		self.assertIsNotNone(response["ticket"]["check_in_time"])
		self.assertTrue(frappe.db.exists("Event Check In", {"ticket": self.ticket}))

	def test_second_checkin_same_day_is_rejected(self):
		checkin_ticket(self.ticket)
		frappe.clear_messages()

		with self.assertRaises(AlreadyCheckedIn):
			checkin_ticket(self.ticket)

		self.assertIn("already checked in today", frappe.local.message_log[-1]["message"])

	def test_validation_rejects_an_already_checked_in_ticket(self):
		checkin_ticket(self.ticket)

		with self.assertRaises(AlreadyCheckedIn):
			validate_ticket_for_checkin(self.ticket)


class TestCheckinAccess(IntegrationTestCase):
	"""Front-desk work is for the event's own team, at Frontdesk or above."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		owner = UserFactory.create_once("checkin-owner@example.com").name
		other_owner = UserFactory.create_once("checkin-other-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(owner).name
		cls.other_team = BuzzTeamFactory.create_owned_by(other_owner).name
		cls.event = str(BuzzEventFactory.create(team=cls.team).name)
		cls.other_event = str(BuzzEventFactory.create(team=cls.other_team).name)

		cls.frontdesk = cls.member("checkin-frontdesk@example.com", "Frontdesk")
		cls.manager = cls.member("checkin-manager@example.com", "Manager")
		cls.viewer = cls.member("checkin-viewer@example.com", "Viewer")
		# Front desk on one team, only a Viewer on the other.
		BuzzTeamMembershipFactory.create(team=cls.other_team, user=cls.frontdesk, team_role="Viewer")

	@classmethod
	def member(cls, email: str, team_role: str) -> str:
		user = UserFactory.create_once(email).name
		BuzzTeamMembershipFactory.create(team=cls.team, user=user, team_role=team_role)
		return user

	def setUp(self):
		frappe.clear_messages()

	def test_frontdesk_and_manager_can_check_in(self):
		for user in (self.frontdesk, self.manager):
			ticket = EventTicketFactory.create(event=self.event).name
			with self.set_user(user):
				self.assertTrue(checkin_ticket(ticket).ticket.is_checked_in)

	def test_viewer_cannot_check_in(self):
		ticket = EventTicketFactory.create(event=self.event).name
		with self.set_user(self.viewer), self.assertRaises(NotPermitted):
			validate_ticket_for_checkin(ticket)

	def test_frontdesk_role_does_not_carry_to_another_team(self):
		ticket = EventTicketFactory.create(event=self.other_event).name
		with self.set_user(self.frontdesk), self.assertRaises(NotPermitted):
			checkin_ticket(ticket)

	def test_events_list_only_the_front_desk_teams(self):
		with self.set_user(self.frontdesk):
			events = {event.name for event in get_checkin_events()}

		self.assertIn(self.event, events)
		self.assertNotIn(self.other_event, events)

	def test_viewer_cannot_open_the_guest_list(self):
		with self.set_user(self.viewer), self.assertRaises(NotPermitted):
			get_checkin_guests(self.event)

	def test_guest_list_splits_on_todays_check_in(self):
		event = str(BuzzEventFactory.create(team=self.team).name)
		arrived, waiting = (EventTicketFactory.create("submitted", event=event).name for _ in range(2))
		with self.set_user(self.frontdesk):
			checkin_ticket(arrived)
			everyone = get_checkin_guests(event).__json__()
			checked_in = get_checkin_guests(event, checked_in="1").__json__()
			not_checked_in = get_checkin_guests(event, checked_in="0").__json__()

		self.assertEqual(everyone["checked_in"], 1)
		self.assertEqual([guest["name"] for guest in checked_in["guests"]], [arrived])
		self.assertIsNotNone(checked_in["guests"][0]["checked_in_at"])
		self.assertEqual([guest["name"] for guest in not_checked_in["guests"]], [waiting])
		self.assertEqual(not_checked_in["matched"], 1)
