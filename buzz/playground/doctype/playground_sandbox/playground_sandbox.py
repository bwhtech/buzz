# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PlaygroundSandbox(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attendee: DF.Link | None
		expires_on: DF.Datetime
		front_desk: DF.Link | None
		organizer: DF.Link
		team: DF.Link
	# end: auto-generated types

	@property
	def personas(self) -> list[str]:
		return [user for user in (self.organizer, self.attendee, self.front_desk) if user]
