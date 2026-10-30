# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from buzz.events.doctype.buzz_schedule_item_type.buzz_schedule_item_type import HEX_COLOR

THEME_COLORS = frozenset(
	{"gray", "blue", "green", "red", "orange", "yellow", "teal", "cyan", "purple", "pink"}
)


def validate_color(color: str | None):
	if color and color not in THEME_COLORS and not HEX_COLOR.match(color):
		frappe.throw(_("<b>Color</b> must be a theme color such as blue, or a hex value such as #2563eb"))


class BuzzScheduleTrack(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		capacity: DF.Int
		color: DF.Data | None
		event: DF.Link | None
		is_standard: DF.Check
		schedule: DF.Link | None
		sequence: DF.Int
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		validate_color(self.color)
		if self.is_standard:
			self.schedule = self.event = None
