# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


class BuzzScheduleItemType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		color: DF.Color | None
		default_duration: DF.Int
		icon: DF.Data | None
		is_standard: DF.Check
		spans_all_tracks: DF.Check
		team: DF.Link | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if self.color and not HEX_COLOR.match(self.color):
			frappe.throw(_("<b>Color</b> must be a hex value such as #2563eb"))
		if self.is_standard:
			self.team = None
		elif not self.team:
			frappe.throw(_("<b>Team</b> is required for a type that is not standard"))
