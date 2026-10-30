# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from buzz import telemetry
from buzz.events.doctype.event_check_in_zone.event_check_in_zone import default_zone


class EventCheckIn(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		date: DF.Date | None
		event: DF.Link
		ticket: DF.Link
		zone: DF.Link
	# end: auto-generated types

	def before_insert(self):
		if not self.date:
			self.date = frappe.utils.today()
		if not self.zone:
			self.zone = default_zone(self.event)

	def validate(self):
		if not self.zone:
			frappe.throw(_("This event has no check-in zone."))
		# Buzz Event is autoincrement-named, so the link value may arrive as an int.
		if str(frappe.db.get_value("Event Check-in Zone", self.zone, "event")) != str(self.event):
			frappe.throw(_("The zone belongs to another event."))

	def on_submit(self):
		telemetry.capture("ticket_checked_in")
