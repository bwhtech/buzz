# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from buzz.utils import generate_qr_code_file, is_app_installed


class BuzzCampaign(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.MarkdownEditor
		enabled: DF.Check
		event: DF.Link | None
		qr_code: DF.AttachImage | None
		title: DF.Data
	# end: auto-generated types

	def before_save(self):
		if not self.enabled:
			return

		previous = self.get_doc_before_save()
		name_changed = previous and previous.name != self.name
		if not self.qr_code or name_changed:
			self.generate_qr_code()

	def validate(self):
		self.validate_crm_installed()

	def validate_crm_installed(self):
		if self.enabled and not is_app_installed("crm"):
			frappe.throw(_("Please install Frappe CRM to use campaigns feature"))

	def generate_qr_code(self):
		register_url = f"{frappe.utils.get_url()}/b/register-interest/{self.name}"
		self.qr_code = generate_qr_code_file(
			doc=self,
			data=register_url,
			field_name="qr_code",
			file_prefix="campaign-qr-code",
		)
