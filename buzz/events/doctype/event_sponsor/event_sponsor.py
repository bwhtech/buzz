# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EventSponsor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company_logo: DF.AttachImage
		company_name: DF.Data
		contact_email: DF.Data | None
		country: DF.Link | None
		enquiry: DF.Link | None
		event: DF.Link
		tier: DF.Link
		website: DF.Data | None
	# end: auto-generated types

	def on_trash(self):
		"""The enquiry it came from is settled but no longer listed, so it reads as cancelled."""
		if self.enquiry and frappe.db.exists("Sponsorship Enquiry", self.enquiry):
			frappe.db.set_value("Sponsorship Enquiry", self.enquiry, "status", "Cancelled")

	def validate(self):
		if not self.enquiry:
			return

		already_exists = frappe.db.exists(
			"Event Sponsor", {"event": self.event, "enquiry": self.enquiry, "name": ("!=", self.name)}
		)

		if already_exists:
			frappe.throw(frappe._("Sponsor for this enquiry already exists!"))
