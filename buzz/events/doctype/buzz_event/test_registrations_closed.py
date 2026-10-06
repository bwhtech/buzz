from datetime import datetime, time, timedelta, timezone
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from buzz.api.booking.services import are_registrations_closed

# "Now" is mocked, so the day only has to be the same for the event and the clock.
EVENT_DATE = getdate(add_days(today(), 30))
IST = timezone(timedelta(hours=5, minutes=30))
PDT = timezone(timedelta(hours=-7))


class TestRegistrationsClosed(IntegrationTestCase):
	"""`get_datetime_in_timezone` is mocked: it returns "now" already in the event's time zone."""

	def test_no_close_at_and_event_in_future_returns_false(self):
		event = self.event_dict(time_zone="UTC", event_date=str(add_days(EVENT_DATE, 5)))
		self.assertFalse(self.is_closed(event, self.now_at("10:00")))

	def test_no_close_at_falls_back_to_event_end(self):
		event = self.event_dict(time_zone="UTC", end_time="18:00:00")
		self.assertTrue(self.is_closed(event, self.now_at("20:00")))

	def test_close_at_takes_priority_over_event_end(self):
		event = self.event_dict(
			registrations_close_at=self.close_at("20:00"), time_zone="UTC", end_time="18:00:00"
		)
		self.assertFalse(self.is_closed(event, self.now_at("19:00")))

	def test_future_close_at_returns_false(self):
		event = self.event_dict(registrations_close_at=self.close_at("12:00"), time_zone="UTC")
		self.assertFalse(self.is_closed(event, self.now_at("10:00")))

	def test_past_close_at_returns_true(self):
		event = self.event_dict(registrations_close_at=self.close_at("12:00"), time_zone="UTC")
		self.assertTrue(self.is_closed(event, self.now_at("14:00")))

	def test_timezone_ahead_of_utc_closes_earlier(self):
		event = self.event_dict(registrations_close_at=self.close_at("18:00"), time_zone="Asia/Kolkata")
		self.assertTrue(self.is_closed(event, self.now_at("19:30", IST)))

	def test_timezone_behind_utc_stays_open_longer(self):
		event = self.event_dict(registrations_close_at=self.close_at("18:00"), time_zone="US/Pacific")
		self.assertFalse(self.is_closed(event, self.now_at("16:00", PDT)))

	def test_same_close_time_different_timezones(self):
		close_time = self.close_at("18:00")
		event_ist = self.event_dict(registrations_close_at=close_time, time_zone="Asia/Kolkata")
		event_pdt = self.event_dict(registrations_close_at=close_time, time_zone="US/Pacific")

		self.assertTrue(self.is_closed(event_ist, self.now_at("23:00", IST)))
		self.assertFalse(self.is_closed(event_pdt, self.now_at("10:30", PDT)))

	def test_falls_back_to_system_timezone_when_event_tz_not_set(self):
		event = self.event_dict(registrations_close_at=self.close_at("13:00"), time_zone=None)
		self.assertTrue(self.is_closed(event, self.now_at("14:00")))

	def test_closing_moment_is_same_absolute_instant_for_viewers_anywhere(self):
		# Strictly greater-than: the exact closing instant is still open.
		event = self.event_dict(registrations_close_at=self.close_at("16:30"), time_zone="Asia/Kolkata")

		self.assertFalse(self.is_closed(event, self.now_at("16:29", IST)))
		self.assertFalse(self.is_closed(event, self.now_at("16:30", IST)))
		self.assertTrue(self.is_closed(event, self.now_at("16:31", IST)))

	def test_event_end_fallback_is_also_timezone_consistent(self):
		event = self.event_dict(time_zone="Asia/Kolkata", end_time="16:30:00")

		self.assertFalse(self.is_closed(event, self.now_at("16:29", IST)))
		self.assertTrue(self.is_closed(event, self.now_at("16:31", IST)))

	def event_dict(self, registrations_close_at=None, time_zone=None, event_date=None, end_time="18:00:00"):
		return frappe._dict(
			registrations_close_at=registrations_close_at,
			time_zone=time_zone,
			start_date=event_date or str(EVENT_DATE),
			start_time="09:00:00",
			end_date=event_date or str(EVENT_DATE),
			end_time=end_time,
		)

	def now_at(self, time_of_day: str, tzinfo: timezone | None = None) -> datetime:
		return datetime.combine(EVENT_DATE, time.fromisoformat(time_of_day), tzinfo)

	def close_at(self, time_of_day: str) -> str:
		return f"{EVENT_DATE} {time_of_day}:00"

	def is_closed(self, event, now: datetime) -> bool:
		with patch("buzz.api.booking.services.get_datetime_in_timezone", return_value=now):
			return are_registrations_closed(event)
