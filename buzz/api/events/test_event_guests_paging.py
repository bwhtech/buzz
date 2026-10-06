from datetime import datetime

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_datetime, today

from buzz.api.events import get_event_guests
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, EventTicketFactory, UserFactory


class TestGetEventGuestsPaging(IntegrationTestCase):
	"""Search, order and paging — the arguments the guest list walks the roll with."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("paging-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name

	def setUp(self):
		self.event = str(BuzzEventFactory.create(team=self.team).name)

	def test_carries_the_time_the_ticket_was_raised(self):
		registered_at = self.register("Ana", "Diaz", days_ago=3)

		self.assertEqual(self.guests().guests[0].registered_at, registered_at)

	def test_newest_registration_comes_first_by_default(self):
		self.roll_call()

		self.assertEqual(self.names(self.guests()), ["Cy Ferreira", "Bo Chen", "Ana Diaz"])

	def test_asc_walks_from_the_oldest_registration(self):
		self.roll_call()

		self.assertEqual(self.names(self.guests(order="asc")), ["Ana Diaz", "Bo Chen", "Cy Ferreira"])

	def test_an_unknown_order_falls_back_to_newest_first(self):
		self.roll_call()

		guests = self.guests(order="name desc; drop table")

		self.assertEqual(guests.guests[0].attendee_name, "Cy Ferreira")

	def test_a_page_carries_only_its_own_slice(self):
		self.roll_call()

		first = self.guests(limit=2)

		self.assertEqual(self.names(first), ["Cy Ferreira", "Bo Chen"])
		self.assertTrue(first.has_next_page)

	def test_the_last_page_says_there_is_nothing_after_it(self):
		self.roll_call()

		last = self.guests(start=2, limit=2)

		self.assertEqual(self.names(last), ["Ana Diaz"])
		self.assertFalse(last.has_next_page)

	def test_a_full_final_page_is_still_the_end(self):
		"""Four guests read two at a time: the second page fills, and nothing follows."""
		self.roll_call()
		self.register("Di", "Okafor", days_ago=0)

		self.assertFalse(self.guests(start=2, limit=2).has_next_page)

	def test_search_matches_a_name(self):
		self.roll_call()

		self.assertEqual(self.names(self.guests(search="chen")), ["Bo Chen"])

	def test_search_matches_an_email(self):
		self.roll_call()

		guests = self.guests(search="cy@")

		self.assertEqual([guest.attendee_email for guest in guests.guests], ["cy@example.com"])

	def test_search_reports_the_match_count_beside_the_registered_count(self):
		self.roll_call()

		guests = self.guests(search="chen")

		self.assertEqual((guests.total, guests.matched), (3, 1))

	def test_without_a_search_every_guest_is_a_match(self):
		self.roll_call()

		guests = self.guests()

		self.assertEqual(guests.matched, guests.total)

	def test_a_search_that_matches_nobody_is_empty_rather_than_an_error(self):
		self.roll_call()

		guests = self.guests(search="nobody-here")

		self.assertEqual(guests.guests, [])
		self.assertEqual((guests.matched, guests.total), (0, 3))
		self.assertFalse(guests.has_next_page)

	def test_blank_search_is_not_a_filter(self):
		self.roll_call()

		self.assertEqual(len(self.guests(search="   ").guests), 3)

	def roll_call(self):
		self.register("Ana", "Diaz", days_ago=3)
		self.register("Bo", "Chen", days_ago=2)
		self.register("Cy", "Ferreira", days_ago=1)

	def register(self, first_name: str, last_name: str, days_ago: int) -> datetime:
		"""Tickets a test writes land in the same second, so `creation` is set to order them."""
		ticket = EventTicketFactory.create(
			"submitted",
			event=self.event,
			first_name=first_name,
			last_name=last_name,
			attendee_email=f"{first_name.lower()}@example.com",
		)
		registered_at = get_datetime(f"{add_days(today(), -days_ago)} 09:00:00")
		frappe.db.set_value("Event Ticket", ticket.name, "creation", registered_at, update_modified=False)
		return registered_at

	def guests(self, **arguments):
		with self.set_user(self.owner):
			return get_event_guests(self.event, **arguments)

	def names(self, guests) -> list[str]:
		return [guest.attendee_name for guest in guests.guests]
