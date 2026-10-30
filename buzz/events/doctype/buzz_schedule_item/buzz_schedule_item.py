# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, to_timedelta


class BuzzScheduleItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		all_tracks: DF.Check
		date: DF.Date
		duration: DF.Duration | None
		end_time: DF.Time | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_doctype: DF.Link | None
		reference_document: DF.DynamicLink | None
		start_time: DF.Time
		title: DF.Data | None
		track: DF.Link | None
		type: DF.Link
	# end: auto-generated types

	def validate_for(self, schedule):
		self.validate_date(schedule.day_dates())
		self.set_end_time_or_duration()
		self.validate_track(schedule.name)
		self.validate_type(schedule.event_team())
		self.validate_reference(schedule.event)
		self.set_title()

	def throw(self, message: str):
		frappe.throw(_("<b>Items</b> row #{0}: {1}").format(self.idx, message))

	def validate_date(self, day_dates: set):
		if getdate(self.date) not in day_dates:
			self.throw(_("<b>Date</b> must be one of the schedule days"))

	def set_end_time_or_duration(self):
		"""An entered end time wins; otherwise the end is the start plus the duration."""
		start = to_timedelta(self.start_time)
		if self.end_time:
			self.duration = (to_timedelta(self.end_time) - start).total_seconds()
		elif self.duration:
			self.end_time = start + timedelta(seconds=self.duration)
		else:
			self.throw(_("Set an <b>End Time</b> or a <b>Duration</b>"))

		if self.duration <= 0:
			self.throw(_("<b>End Time</b> must be after <b>Start Time</b>"))
		if to_timedelta(self.end_time) >= timedelta(days=1):
			self.throw(_("<b>End Time</b> must be on the same day"))

	def validate_track(self, schedule: str):
		if self.all_tracks:
			self.track = None
			return
		track_schedule, is_standard = frappe.db.get_value(
			"Buzz Schedule Track", self.track, ["schedule", "is_standard"]
		) or (None, 0)
		if not is_standard and track_schedule != schedule:
			self.throw(_("<b>Track</b> must be a standard track or belong to this schedule"))

	def validate_type(self, team: str | None):
		is_standard, type_team = frappe.db.get_value(
			"Buzz Schedule Item Type", self.type, ["is_standard", "team"]
		) or (0, None)
		if not is_standard and type_team != team:
			self.throw(_("<b>Type</b> must be a standard type or one of this team's types"))

	def validate_reference(self, event: str):
		"""The referenced document must belong to this event, or a schedule could publish another team's data."""
		if not self.reference_document:
			return
		if not frappe.get_meta(self.reference_doctype).has_field("event"):
			self.throw(_("<b>Reference Document</b> must belong to an event"))
		reference_event = frappe.db.get_value(self.reference_doctype, self.reference_document, "event")
		if str(reference_event) != str(event):
			self.throw(_("<b>Reference Document</b> must belong to this event"))

	def set_title(self):
		if not self.title:
			self.title = self.reference_title() or frappe.db.get_value(
				"Buzz Schedule Item Type", self.type, "title"
			)

	def reference_title(self) -> str | None:
		if not self.reference_document:
			return None
		title_field = frappe.get_meta(self.reference_doctype).get_title_field()
		return frappe.db.get_value(self.reference_doctype, self.reference_document, title_field)
