from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.checkin import (
	checkin_ticket,
	get_checkin_events,
	get_checkin_guests,
	undo_checkin,
	validate_ticket_for_checkin,
)
from buzz.api.checkin.exceptions import (
	AlreadyCheckedIn,
	NotAllowedInZone,
	NotCheckedIn,
	TicketCancelled,
	TicketNotFound,
)
from buzz.api.events.exceptions import ZoneNotFound
from buzz.api.exceptions import NotPermitted
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventBookingFactory,
	EventCheckinZoneFactory,
	EventPaymentFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
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

		self.assertIn("already checked in at Main Entrance", frappe.local.message_log[-1]["message"])

	def test_validation_at_a_zone_rejects_an_already_checked_in_ticket(self):
		checkin_ticket(self.ticket)
		default = frappe.db.get_value("Event Check-in Zone", {"event": self.event, "is_default": 1})

		with self.assertRaises(AlreadyCheckedIn):
			validate_ticket_for_checkin(self.ticket, zone=default)


class TestCheckinZones(CheckinTestCase):
	def zone(self, *traits, **overrides) -> str:
		return EventCheckinZoneFactory.create(*traits, event=self.event, **overrides).name

	def checkin_rows(self) -> list[str]:
		return frappe.get_all("Event Check In", filters={"ticket": self.ticket, "docstatus": 1}, pluck="zone")

	def test_no_zone_checks_in_at_the_default_zone(self):
		checkin_ticket(self.ticket)

		default = frappe.db.get_value("Event Check-in Zone", {"event": self.event, "is_default": 1})
		self.assertEqual(self.checkin_rows(), [default])

	def test_zones_on_the_same_day_are_independent(self):
		checkin_ticket(self.ticket)
		checkin_ticket(self.ticket, zone=self.zone())

		self.assertEqual(len(self.checkin_rows()), 2)

	def test_once_per_event_refuses_the_next_day(self):
		zone = self.zone("once_per_event")
		checkin_ticket(self.ticket, zone=zone)

		with patch("buzz.api.checkin.services.today", return_value=add_days(today(), 1)):
			with self.assertRaises(AlreadyCheckedIn):
				checkin_ticket(self.ticket, zone=zone)

	def test_once_per_day_allows_the_next_day(self):
		checkin_ticket(self.ticket)

		with patch("buzz.api.checkin.services.today", return_value=add_days(today(), 1)):
			checkin_ticket(self.ticket)

		self.assertEqual(len(self.checkin_rows()), 2)

	def test_a_ticket_type_rule_refuses_other_ticket_types(self):
		vip = EventTicketTypeFactory.create(event=self.event).name
		zone = self.zone(ticket_types=[{"ticket_type": vip}])

		with self.assertRaises(NotAllowedInZone):
			checkin_ticket(self.ticket, zone=zone)

		ticket = EventTicketFactory.create(event=self.event, ticket_type=vip).name
		self.assertTrue(checkin_ticket(ticket, zone=zone).ticket.is_checked_in)

	def test_a_disabled_zone_is_refused(self):
		with self.assertRaises(ZoneNotFound):
			checkin_ticket(self.ticket, zone=self.zone("disabled"))

	def test_a_zone_of_another_event_is_refused(self):
		other_zone = EventCheckinZoneFactory.create().name

		with self.assertRaises(ZoneNotFound):
			validate_ticket_for_checkin(self.ticket, zone=other_zone)

	def test_undo_is_per_zone(self):
		zone = self.zone()
		checkin_ticket(self.ticket, zone=zone)

		with self.assertRaises(NotCheckedIn):
			undo_checkin(self.ticket)

		undo_checkin(self.ticket, zone=zone)
		self.assertEqual(self.checkin_rows(), [])

	def test_validate_with_no_zone_reports_every_zone(self):
		zone = self.zone()
		checkin_ticket(self.ticket)

		zones = validate_ticket_for_checkin(self.ticket).__json__()["zones"]
		added = next(row for row in zones if row["name"] == zone)

		self.assertEqual(zones[0]["title"], "Main Entrance")
		self.assertIsNotNone(zones[0]["checked_in_at"])
		self.assertIsNone(added["checked_in_at"])
		self.assertTrue(added["allowed"])

	def test_guest_list_status_follows_the_zone(self):
		zone = self.zone()
		ticket = EventTicketFactory.create("submitted", event=self.event).name
		checkin_ticket(ticket, zone=zone)

		event = str(self.event)
		at_default = get_checkin_guests(event, checked_in="1").__json__()
		at_zone = get_checkin_guests(event, checked_in="1", zone=zone).__json__()

		self.assertNotIn(ticket, [guest["name"] for guest in at_default["guests"]])
		self.assertIn(ticket, [guest["name"] for guest in at_zone["guests"]])
		self.assertIsNotNone(at_zone["guests"][0]["checked_in_at"])
		self.assertIn(zone, [row["name"] for row in at_zone["zones"]])


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
