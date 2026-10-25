import json

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.checkin import checkin_ticket
from buzz.api.events import get_event, get_event_guests
from buzz.api.events.exceptions import CannotManageEvent, EventNotFound, ZoneNotFound
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventCheckinZoneFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
	TicketAddOnFactory,
	UserFactory,
)


class GuestsTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("guests-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name

	def setUp(self):
		self.event = str(BuzzEventFactory.create(team=self.team, title="Guest List Event").name)

	def guests_as(self, user: str, **arguments):
		with self.set_user(user):
			return get_event_guests(self.event, **arguments)


class TestGetEventGuests(GuestsTestCase):
	def test_counts_and_lists_the_submitted_tickets(self):
		for email in ("guest-one@example.com", "guest-two@example.com"):
			EventTicketFactory.create("submitted", event=self.event, attendee_email=email)

		guests = self.guests_as(self.owner).__json__()

		self.assertEqual(guests["total"], 2)
		emails = {guest["attendee_email"] for guest in guests["guests"]}
		self.assertEqual(emails, {"guest-one@example.com", "guest-two@example.com"})

	def test_leaves_out_a_ticket_that_was_never_submitted(self):
		EventTicketFactory.create(event=self.event)

		self.assertEqual(self.guests_as(self.owner).total, 0)

	def test_carries_the_add_ons_a_ticket_holds(self):
		add_on = TicketAddOnFactory.create(event=self.event, title="T-Shirt").name
		add_ons = [{"add_on": add_on, "value": "Large"}]
		EventTicketFactory.create("submitted", event=self.event, add_ons=add_ons)

		guest = self.guests_as(self.owner).guests[0]

		self.assertEqual([(row.title, row.value) for row in guest.add_ons], [("T-Shirt", "Large")])

	def test_names_the_ticket_type_rather_than_its_docname(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event, title="Early Bird").name
		EventTicketFactory.create("submitted", event=self.event, ticket_type=ticket_type)

		self.assertEqual(self.guests_as(self.owner).guests[0].ticket_type, "Early Bird")

	def test_an_event_with_no_guests_is_empty_rather_than_an_error(self):
		guests = self.guests_as(self.owner)

		self.assertEqual(guests.total, 0)
		self.assertEqual(guests.guests, [])

	def test_names_the_event_for_a_member_who_cannot_edit_it(self):
		"""The header labels the page off this payload, so read access has to be enough."""
		viewer = UserFactory.create_once("guests-viewer@example.com").name
		BuzzTeamMembershipFactory.create(team=self.team, user=viewer, team_role="Viewer")

		self.assertEqual(self.guests_as(viewer).title, "Guest List Event")
		with self.set_user(viewer):
			self.assertFalse(get_event(self.event).can_write)

	def test_a_non_member_cannot_read_the_guest_list(self):
		outsider = UserFactory.create_once("guests-stranger@example.com").name
		EventTicketFactory.create("submitted", event=self.event)

		with self.assertRaises(CannotManageEvent):
			self.guests_as(outsider)

	def test_an_unknown_event_is_not_found(self):
		with self.set_user(self.owner), self.assertRaises(EventNotFound):
			get_event_guests("999999999")


class TestGetEventGuestsTicketTypeFilter(GuestsTestCase):
	def setUp(self):
		super().setUp()
		self.first = self.submit_ticket_on_new_type("early@example.com")
		self.second = self.submit_ticket_on_new_type("late@example.com")

	def test_lists_the_types_the_event_sells(self):
		"""Every type, not only the ones someone has bought — an empty tier is still a filter."""
		unsold = str(EventTicketTypeFactory.create(event=self.event).name)

		filter_fields = self.guests_as(self.owner).filter_fields
		ticket_type = next(field for field in filter_fields if field.key == "ticket_type")

		self.assertLessEqual(
			{self.first, self.second, unsold}, {option.value for option in ticket_type.options}
		)

	def test_narrows_the_list_to_the_chosen_type(self):
		guests = self.guests_as(self.owner, filters=types_filter(self.first))

		self.assertEqual([guest.attendee_email for guest in guests.guests], ["early@example.com"])
		self.assertEqual(guests.matched, 1)
		self.assertEqual(guests.total, 2)

	def test_several_types_are_read_as_any_of_them(self):
		self.assertEqual(self.guests_as(self.owner, filters=types_filter(self.first, self.second)).matched, 2)

	def test_no_chosen_type_is_not_a_filter(self):
		self.assertEqual(len(self.guests_as(self.owner, filters=types_filter()).guests), 2)

	def test_search_and_type_narrow_together(self):
		late = self.guests_as(self.owner, search="late@", filters=types_filter(self.first))
		early = self.guests_as(self.owner, search="early@", filters=types_filter(self.first))

		self.assertEqual((late.matched, early.matched), (0, 1))

	def submit_ticket_on_new_type(self, email: str) -> str:
		"""Each ticket comes on a ticket type of its own."""
		return str(EventTicketFactory.create("submitted", event=self.event, attendee_email=email).ticket_type)


def types_filter(*types: str) -> str:
	return json.dumps([["ticket_type", "in", list(types)]])


class TestGuestZones(GuestsTestCase):
	def setUp(self):
		super().setUp()
		self.vip = str(EventTicketTypeFactory.create(event=self.event).name)
		self.lounge = EventCheckinZoneFactory.create(
			event=self.event, ticket_types=[{"ticket_type": self.vip}]
		).name
		self.general = EventTicketFactory.create("submitted", event=self.event).name
		self.vip_ticket = EventTicketFactory.create("submitted", event=self.event, ticket_type=self.vip).name
		checkin_ticket(self.vip_ticket, zone=self.lounge)

	def test_counts_check_ins_against_the_tickets_each_zone_lets_in(self):
		guests = self.guests_as(self.owner)

		zones = {zone.name: (zone.checked_in, zone.eligible) for zone in guests.zones}
		self.assertEqual(zones[self.lounge], (1, 1))
		self.assertEqual(guests.zones[0].checked_in, 0)
		self.assertEqual(guests.zones[0].eligible, 2)
		self.assertEqual(guests.checked_in_any_zone, 1)

	def test_gives_each_guest_a_status_per_zone(self):
		guests = {guest.name: guest for guest in self.guests_as(self.owner).guests}

		general = {zone.name: zone for zone in guests[self.general].zones}
		self.assertFalse(general[self.lounge].allowed)
		vip = {zone.name: zone for zone in guests[self.vip_ticket].zones}
		self.assertIsNotNone(vip[self.lounge].checked_in_at)

	def test_a_zone_narrows_the_list_to_the_tickets_it_lets_in(self):
		guests = self.guests_as(self.owner, zone=self.lounge)

		self.assertEqual([guest.name for guest in guests.guests], [self.vip_ticket])

	def test_a_disabled_zone_cannot_narrow_the_list(self):
		frappe.db.set_value("Event Check-in Zone", self.lounge, "enabled", 0)

		with self.assertRaises(ZoneNotFound):
			self.guests_as(self.owner, zone=self.lounge)
