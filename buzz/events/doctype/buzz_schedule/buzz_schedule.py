# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, getdate


class BuzzSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.buzz_schedule_item.buzz_schedule_item import BuzzScheduleItem

		days: DF.JSON | None
		event: DF.Link
		is_published: DF.Check
		items: DF.Table[BuzzScheduleItem]
	# end: auto-generated types

	def before_insert(self):
		if not self.days:
			self.days = event_days(self.event)

	def validate(self):
		self.validate_event_unchanged()
		self.normalize_days()
		for item in self.items:
			item.validate_for(self)

	def validate_event_unchanged(self):
		# Tracks keep the event they fetched, so moving a schedule would leave them behind.
		# Not set_only_once: the autoincrement link reads back as an int and never matches.
		before = self.get_doc_before_save()
		if before and str(before.event) != str(self.event):
			frappe.throw(_("<b>Event</b> of a schedule cannot be changed"))

	def day_list(self) -> list[dict]:
		return frappe.parse_json(self.days or "[]")

	def day_dates(self) -> set:
		return {getdate(day["date"]) for day in self.day_list()}

	def event_team(self) -> str | None:
		return frappe.get_cached_value("Buzz Event", self.event, "team")

	def normalize_days(self):
		if not all(isinstance(day, dict) and day.get("date") for day in self.day_list()):
			frappe.throw(_("Each schedule day needs a date"))
		days = [
			{"date": str(getdate(day["date"])), "label": day.get("label") or ""} for day in self.day_list()
		]
		if len({day["date"] for day in days}) != len(days):
			frappe.throw(_("Each schedule day must have a different date"))
		self.days = frappe.as_json(days)


def event_days(event: str) -> str:
	"""One day per date the event spans, labeled Day 1 to Day N."""
	start_date, end_date = frappe.db.get_value("Buzz Event", event, ["start_date", "end_date"])
	count = date_diff(end_date or start_date, start_date) + 1
	return frappe.as_json(
		[
			{"date": str(add_days(start_date, offset)), "label": _("Day {0}").format(offset + 1)}
			for offset in range(count)
		]
	)
