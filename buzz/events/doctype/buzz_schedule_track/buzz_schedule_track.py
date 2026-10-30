# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from buzz.events.doctype.buzz_schedule_item_type.buzz_schedule_item_type import validate_color


class BuzzScheduleTrack(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		color: DF.Data | None
		event: DF.Link | None
		schedule: DF.Link
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		validate_color(self.color)
