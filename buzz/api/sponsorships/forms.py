from functools import cached_property

import frappe
from frappe import _

from buzz.api.forms.answers import CustomAnswers
from buzz.api.forms.exceptions import FormNotAvailable, LoginRequired, SubmissionsClosed
from buzz.api.forms.fields import get_form_fields
from buzz.api.forms.schemas import CustomFieldDefinition
from buzz.api.forms.services import CustomFormService
from buzz.events.doctype.sponsor_enquiry_form.sponsor_enquiry_form import ENQUIRY_FIELDS


class SponsorFormService(CustomFormService):
	def form_data(self):
		response = super().form_data()
		response.submission_method = "buzz.api.sponsorships.submit_enquiry_form"
		return response

	@cached_property
	def form_row(self):
		name = frappe.db.get_value(
			"Sponsor Enquiry Form", {"event": self.event.name, "route": self.form_route, "publish": 1}
		)
		if not name:
			FormNotAvailable.throw()
		return frappe.get_doc("Sponsor Enquiry Form", name)

	@property
	def form_doctype(self):
		return "Sponsorship Enquiry"

	def check_login(self):
		if not self.form_row.allow_guest_submissions and frappe.session.user == "Guest":
			LoginRequired.throw()

	@property
	def exclude_fields(self):
		internal = {
			field.fieldname
			for field in frappe.get_meta(self.form_doctype).fields
			if field.fieldtype not in ("Section Break", "Column Break")
		} - ENQUIRY_FIELDS
		# A signed-in applicant is already named by `owner`, so the address that grants
		# access is never theirs to type. Only a guest supplies one.
		if frappe.session.user != "Guest":
			internal.add("contact_email")
		return super().exclude_fields | internal

	def renderable_fields(self):
		fields = get_form_fields(
			self.form_doctype, self.exclude_fields, with_layout_breaks=True, event=self.event.name
		)
		for field in fields:
			if field["fieldname"] == "contact_email":
				field["reqd"] = 1
		return fields

	def custom_field_definitions(self):
		return [
			CustomFieldDefinition(
				label=row.label,
				fieldname=row.fieldname,
				fieldtype=row.fieldtype,
				options=row.options,
				mandatory=row.mandatory,
				placeholder=row.placeholder,
				default_value=row.default_value,
				order=row.idx,
			)
			for row in self.form_row.custom_fields
			if row.enabled
		]

	def submit(self, data, custom_fields_data=None) -> str:
		self.check_login()
		if self.is_closed:
			SubmissionsClosed.throw()
		values = frappe.parse_json(data) or {}
		if not isinstance(values, dict):
			frappe.throw(_("Form values must be an object."))
		doc = frappe.get_doc(self.build_doc_data(values))
		doc.enquiry_form = self.form_row.name
		doc.set(
			"additional_fields",
			CustomAnswers(self.form_row.custom_fields).rows(frappe.parse_json(custom_fields_data) or {}),
		)
		if doc.tier and str(frappe.db.get_value("Sponsorship Tier", doc.tier, "event")) != str(
			self.event.name
		):
			frappe.throw(_("Select a sponsorship tier from this event."))
		return doc.insert(ignore_permissions=True).name
