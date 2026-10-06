from datetime import datetime, time, timedelta, timezone
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, today

from buzz.api.booking.services import are_registrations_closed

# "Now" is mocked, so the day only has to be the same for the event and the clock.
DAY = getdate(add_days(today(), 30))
IST = timezone(timedelta(hours=5, minutes=30))
PDT = timezone(timedelta(hours=-7))


class TestRegistrationsClosed(IntegrationTestCase):
	"""`get_datetime_in_timezone` is mocked: it returns "now" already in the event's time zone."""

	def test_no_close_at_and_event_in_future_returns_false(self):
		event = make_event(time_zone="UTC", event_date=str(add_days(DAY, 5)))
		self.assertFalse(closed_at(event, at("10:00")))

	def test_no_close_at_falls_back_to_event_end(self):
		# Issue #91: registrations close once the event itself has ended.
		event = make_event(time_zone="UTC", end_time="18:00:00")
		self.assertTrue(closed_at(event, at("20:00")))

	def test_close_at_takes_priority_over_event_end(self):
		event = make_event(registrations_close_at=on_day("20:00"), time_zone="UTC", end_time="18:00:00")
		self.assertFalse(closed_at(event, at("19:00")))

	def test_future_close_at_returns_false(self):
		event = make_event(registrations_close_at=on_day("12:00"), time_zone="UTC")
		self.assertFalse(closed_at(event, at("10:00")))

	def test_past_close_at_returns_true(self):
		event = make_event(registrations_close_at=on_day("12:00"), time_zone="UTC")
		self.assertTrue(closed_at(event, at("14:00")))

	def test_timezone_ahead_of_utc_closes_earlier(self):
		# 14:00 UTC is 19:30 IST, past an 18:00 close in the event's zone.
		event = make_event(registrations_close_at=on_day("18:00"), time_zone="Asia/Kolkata")
		self.assertTrue(closed_at(event, at("19:30", IST)))

	def test_timezone_behind_utc_stays_open_longer(self):
		# 23:00 UTC is 16:00 PDT, before an 18:00 close in the event's zone.
		event = make_event(registrations_close_at=on_day("18:00"), time_zone="US/Pacific")
		self.assertFalse(closed_at(event, at("16:00", PDT)))

	def test_same_close_time_different_timezones(self):
		# 17:30 UTC is 23:00 IST (closed) and 10:30 PDT (open).
		close_at = on_day("18:00")
		event_ist = make_event(registrations_close_at=close_at, time_zone="Asia/Kolkata")
		event_pdt = make_event(registrations_close_at=close_at, time_zone="US/Pacific")

		self.assertTrue(closed_at(event_ist, at("23:00", IST)))
		self.assertFalse(closed_at(event_pdt, at("10:30", PDT)))

	def test_falls_back_to_system_timezone_when_event_tz_not_set(self):
		event = make_event(registrations_close_at=on_day("13:00"), time_zone=None)
		self.assertTrue(closed_at(event, at("14:00")))

	def test_closing_moment_is_same_absolute_instant_for_viewers_anywhere(self):
		# Only the event's zone counts, never the viewer's: 16:30 IST is noon in London (BST).
		# The comparison is strictly greater-than, so the exact closing instant is still open.
		event = make_event(registrations_close_at=on_day("16:30"), time_zone="Asia/Kolkata")

		self.assertFalse(closed_at(event, at("16:29", IST)))
		self.assertFalse(closed_at(event, at("16:30", IST)))
		self.assertTrue(closed_at(event, at("16:31", IST)))

	def test_event_end_fallback_is_also_timezone_consistent(self):
		event = make_event(time_zone="Asia/Kolkata", end_time="16:30:00")

		self.assertFalse(closed_at(event, at("16:29", IST)))
		self.assertTrue(closed_at(event, at("16:31", IST)))


def make_event(registrations_close_at=None, time_zone=None, event_date=None, end_time="18:00:00"):
	"""A minimal event dict: `are_registrations_closed` needs no saved event."""
	return frappe._dict(
		registrations_close_at=registrations_close_at,
		time_zone=time_zone,
		start_date=event_date or str(DAY),
		start_time="09:00:00",
		end_date=event_date or str(DAY),
		end_time=end_time,
	)


def at(time_of_day: str, tzinfo: timezone | None = None) -> datetime:
	return datetime.combine(DAY, time.fromisoformat(time_of_day), tzinfo)


def on_day(time_of_day: str) -> str:
	return f"{DAY} {time_of_day}:00"


def closed_at(event, now: datetime) -> bool:
	with patch("buzz.api.booking.services.get_datetime_in_timezone", return_value=now):
		return are_registrations_closed(event)
