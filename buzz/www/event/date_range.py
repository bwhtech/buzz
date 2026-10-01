from frappe import _
from frappe.utils import format_date, get_time, getdate

RANGE_SEPARATOR = " \u2013 "


def format_time(time) -> str:
	return get_time(time).strftime("%H:%M") if time else ""


class EventDateRange:
	def __init__(self, event):
		self.start_date = getdate(event.start_date)
		self.end_date = getdate(event.end_date or event.start_date)
		self.start_time = event.start_time
		self.end_time = event.end_time

	@property
	def is_multi_day(self) -> bool:
		return self.end_date > self.start_date

	@property
	def is_same_month(self) -> bool:
		return (self.start_date.year, self.start_date.month) == (self.end_date.year, self.end_date.month)

	@property
	def is_same_year(self) -> bool:
		return self.start_date.year == self.end_date.year

	def as_dict(self) -> dict:
		if not self.is_multi_day:
			return {"is_multi_day": False}
		return {
			"is_multi_day": True,
			"day_count_label": _("{0} days").format((self.end_date - self.start_date).days + 1),
			"short_date_range": self.short_date_range(),
			"date_range_with_weekdays": self.date_range_with_weekdays(),
			"full_date_range": self.full_date_range(),
			"start": self.date_and_time(self.start_date, self.start_time),
			"end": self.date_and_time(self.end_date, self.end_time),
		}

	def short_date_range(self) -> str:
		if self.is_same_month:
			return f"{self.start_date.day}\u2013{format_date(self.end_date, 'd MMM')}"
		pattern = "d MMM" if self.is_same_year else "d MMM y"
		return self.format_range(pattern, pattern)

	def date_range_with_weekdays(self) -> str:
		if self.is_same_month:
			return self.format_range("EEE d", "EEE d MMM")
		pattern = "EEE d MMM" if self.is_same_year else "EEE d MMM y"
		return self.format_range(pattern, pattern)

	def full_date_range(self) -> str:
		pattern = "EEEE d MMMM y"
		return _("{0} to {1}").format(
			format_date(self.start_date, pattern), format_date(self.end_date, pattern)
		)

	def date_and_time(self, date, time) -> dict:
		return {
			"date": f"{format_date(date, 'EEE d MMM')} \u2019{date:%y}",
			"time": format_time(time),
		}

	def format_range(self, start_pattern: str, end_pattern: str) -> str:
		start = format_date(self.start_date, start_pattern)
		return f"{start}{RANGE_SEPARATOR}{format_date(self.end_date, end_pattern)}"
