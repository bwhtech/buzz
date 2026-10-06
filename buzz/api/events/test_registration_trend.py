import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from buzz.api.events import get_event_registration_trend
from buzz.api.events.exceptions import CannotManageEvent, EventNotFound
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
	UserFactory,
)


class TestGetEventRegistrationTrend(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("trend-owner@example.com").name
		cls.stranger = UserFactory.create_once("trend-stranger@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name

	def setUp(self):
		self.event = str(BuzzEventFactory.create(team=self.team).name)

	def test_counts_the_tickets_raised_on_each_day(self):
		self.register_on(today())
		self.register_on(today())
		self.register_on(add_days(today(), -1))

		trend = self.trend(days=3)

		totals = totals_by_day(trend)
		self.assertEqual(totals[getdate(today())], 2)
		self.assertEqual(totals[getdate(add_days(today(), -1))], 1)
		self.assertEqual(trend.total, 3)

	def test_splits_a_day_by_ticket_type(self):
		for title in ("Early Bird", "Regular"):
			self.register_on(today(), self.ticket_type(title))

		trend = self.trend(days=2)

		today_rows = {row.ticket_type: row.count for row in trend.per_day if row.date == getdate(today())}
		self.assertEqual((today_rows["Early Bird"], today_rows["Regular"]), (1, 1))

	def test_a_quiet_day_is_a_zero_rather_than_a_gap(self):
		self.register_on(today())

		totals = totals_by_day(self.trend(days=7))

		self.assertEqual(len(totals), 7)
		self.assertEqual(sorted(totals.values()), [0] * 6 + [1])

	def test_every_type_is_drawn_on_every_day(self):
		"""A band that vanishes mid-stack reads as a break in the chart, not as nobody buying."""
		self.register_on(today())

		trend = self.trend(days=4)

		types = {row.ticket_type for row in trend.per_day}
		self.assertEqual(len(trend.per_day), 4 * len(types))

	def test_the_window_ends_on_today(self):
		self.register_on(today())

		trend = self.trend(days=5)

		self.assertEqual(trend.per_day[-1].date, getdate(today()))
		self.assertEqual(trend.per_day[0].date, getdate(add_days(today(), -4)))

	def test_names_the_ticket_type_rather_than_its_docname(self):
		ticket_type = self.ticket_type("Early Bird")
		self.register_on(today(), ticket_type)

		names = {row.ticket_type for row in self.trend(days=2).per_day}

		self.assertIn("Early Bird", names)
		self.assertNotIn(str(ticket_type), names)

	def test_leaves_out_a_ticket_that_was_never_submitted(self):
		EventTicketFactory.create(event=self.event)

		trend = self.trend()

		self.assertEqual(trend.total, 0)
		self.assertEqual({row.count for row in trend.per_day}, {0})

	def test_the_type_breakdown_counts_registrations_older_than_the_window(self):
		"""It sits beside the all-time total, so a fortnight's slice would not add up to it."""
		self.register_on(add_days(today(), -60))

		trend = self.trend(days=7)

		self.assertEqual(sum(row.count for row in trend.by_ticket_type), trend.total)
		self.assertEqual({row.count for row in trend.per_day}, {0})

	def test_the_type_breakdown_names_the_type_rather_than_its_docname(self):
		self.register_on(today(), self.ticket_type("Early Bird"))

		self.assertIn("Early Bird", {row.ticket_type for row in self.trend().by_ticket_type})

	def test_a_non_member_cannot_read_the_trend(self):
		with self.set_user(self.stranger), self.assertRaises(CannotManageEvent):
			get_event_registration_trend(self.event)

	def test_an_unknown_event_is_not_found(self):
		with self.assertRaises(EventNotFound):
			self.trend(event="999999999")

	def register_on(self, day: str, ticket_type: str | None = None):
		# A None override would beat the factory's own new ticket type.
		ticket_type_override = {"ticket_type": ticket_type} if ticket_type else {}
		ticket = EventTicketFactory.create("submitted", event=self.event, **ticket_type_override)
		frappe.db.set_value("Event Ticket", ticket.name, "creation", f"{day} 10:00:00", update_modified=False)

	def ticket_type(self, title: str) -> str:
		return EventTicketTypeFactory.create(event=self.event, title=title).name

	def trend(self, event: str | None = None, **arguments):
		with self.set_user(self.owner):
			return get_event_registration_trend(event or self.event, **arguments)


def totals_by_day(trend) -> dict:
	"""The stack's own height: every type of a day summed back together."""
	totals: dict = {}
	for row in trend.per_day:
		totals[row.date] = totals.get(row.date, 0) + row.count
	return totals
