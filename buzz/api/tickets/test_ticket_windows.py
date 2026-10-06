import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.tickets.windows import ADD_ON_CHANGE, CANCELLATION, TRANSFER, is_window_open
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory

CUTOFF_FIELDS = (TRANSFER, ADD_ON_CHANGE, CANCELLATION)


class TestWindows(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		event = BuzzEventFactory.create()
		cls.event, cls.team = event.name, event.team

	def setUp(self):
		# The rollback restores these rows but not their cached copies.
		self.addCleanup(frappe.clear_document_cache, "Buzz Team Settings", self.team)
		self.addCleanup(frappe.clear_document_cache, "Buzz Event", self.event)
		BuzzTeamFactory.set_settings(self.team, dict.fromkeys(CUTOFF_FIELDS, 7))

	def test_open_while_the_event_is_beyond_the_cutoff(self):
		self.set_event_start(30)
		self.assertTrue(is_window_open(self.event, TRANSFER))

	def test_closed_once_inside_the_cutoff(self):
		self.set_event_start(3)
		self.assertFalse(is_window_open(self.event, TRANSFER))

	def test_exactly_on_the_cutoff_is_still_open(self):
		self.set_event_start(7)
		self.assertTrue(is_window_open(self.event, TRANSFER))

	def test_a_zero_cutoff_keeps_the_window_open_until_the_day(self):
		# Regression: a 0 cutoff must stay 0, not fall back to the 7-day default.
		BuzzTeamFactory.set_settings(self.team, dict.fromkeys(CUTOFF_FIELDS, 0))
		self.set_event_start(1)
		self.assertTrue(is_window_open(self.event, TRANSFER))

	def test_an_event_without_a_start_date_is_closed(self):
		self.set_event_start(None)
		self.assertFalse(is_window_open(self.event, TRANSFER))

	def set_event_start(self, days_from_today: int | None):
		start_date = None if days_from_today is None else add_days(today(), days_from_today)
		frappe.db.set_value("Buzz Event", self.event, "start_date", start_date)
		frappe.clear_document_cache("Buzz Event", self.event)


class TestPerTeamWindows(IntegrationTestCase):
	def test_each_team_enforces_its_own_window(self):
		strict = self.create_team_event(cutoff_days=7, days_from_today=5)
		lenient = self.create_team_event(cutoff_days=2, days_from_today=5)

		for cutoff_fieldname in CUTOFF_FIELDS:
			with self.subTest(cutoff_fieldname=cutoff_fieldname):
				self.assertFalse(is_window_open(strict, cutoff_fieldname))
				self.assertTrue(is_window_open(lenient, cutoff_fieldname))

	def test_an_explicit_zero_cutoff_is_not_treated_as_unset(self):
		event = self.create_team_event(cutoff_days=0, days_from_today=1)

		self.assertTrue(is_window_open(event, TRANSFER))

	def create_team_event(self, cutoff_days: int, days_from_today: int):
		team = BuzzTeamFactory.create_owned_by().name
		BuzzTeamFactory.set_settings(team, dict.fromkeys(CUTOFF_FIELDS, cutoff_days))
		start_date = add_days(today(), days_from_today)
		return BuzzEventFactory.create(team=team, start_date=start_date, end_date=start_date).name
