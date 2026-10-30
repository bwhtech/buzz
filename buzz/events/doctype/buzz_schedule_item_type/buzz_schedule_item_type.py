# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document

THEME_COLORS = frozenset(
	{"gray", "blue", "green", "red", "orange", "yellow", "teal", "cyan", "purple", "pink"}
)
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def validate_color(color: str | None):
	if color and color not in THEME_COLORS and not HEX_COLOR.match(color):
		frappe.throw(_("<b>Color</b> must be a theme color such as blue, or a hex value such as #2563eb"))


class BuzzScheduleItemType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		color: DF.Data | None
		icon: DF.Data | None
		is_standard: DF.Check
		team: DF.Link | None
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		validate_color(self.color)
		if self.is_standard:
			self.team = None
		elif not self.team:
			frappe.throw(_("<b>Team</b> is required for a type that is not standard"))
