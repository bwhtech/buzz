from functools import cached_property

import frappe
from frappe import _

from buzz.api.forms.answers import CustomAnswers
from buzz.api.forms.exceptions import FormNotAvailable, SubmissionsClosed
from buzz.api.forms.fields import get_form_fields
from buzz.api.forms.schemas import CustomFieldDefinition
from buzz.api.forms.services import CustomFormService
from buzz.events.doctype.sponsor_enquiry_form.sponsor_enquiry_form import ENQUIRY_FIELDS

ENQUIRY_DOCTYPE = "Sponsorship Enquiry"
SUBMISSION_METHOD = "buzz.api.sponsorships.submit_enquiry_form"


class SponsorFormService(CustomFormService):
	"""Serve the event's Sponsor Enquiry Form through the shared custom form machinery."""

	def form_data(self):
		response = super().form_data()
		response.submission_method = SUBMISSION_METHOD
		return response

	@cached_property
	def form(self):
		"""The event's published Sponsor Enquiry Form, in place of a custom_forms row."""
		form_id = frappe.db.get_value(
			"Sponsor Enquiry Form", {"event": self.event.name, "route": self.form_route, "publish": 1}
		)
		if not form_id:
			FormNotAvailable.throw()
		return frappe.get_doc("Sponsor Enquiry Form", form_id)

	@property
	def form_doctype(self):
		return ENQUIRY_DOCTYPE

	def check_login(self):
		"""Sponsor enquiry forms are always public."""

	@property
	def exclude_fields(self):
		"""Hide every enquiry field except the ones an applicant is meant to fill in."""
		internal = {
			field.fieldname
			for field in frappe.get_meta(self.form_doctype).fields
			if field.fieldtype not in ("Section Break", "Column Break")
		} - ENQUIRY_FIELDS
		# Every applicant gives a contact address, even on forms saved while it could be hidden.
		return (super().exclude_fields | internal) - {"contact_email"}

	def renderable_fields(self):
		fields = get_form_fields(
			self.form_doctype, self.exclude_fields, with_layout_breaks=True, event=self.event.name
		)
		for field in fields:
			if field["fieldname"] == "contact_email":
				field["reqd"] = 1
				field["default"] = session_user_email()
		return fields

	def custom_field_definitions(self):
		return [
			CustomFieldDefinition(
				label=question.label,
				fieldname=question.fieldname,
				fieldtype=question.fieldtype,
				options=question.options,
				mandatory=question.mandatory,
				placeholder=question.placeholder,
				default_value=question.default_value,
				order=question.idx,
			)
			for question in self.form.custom_fields
			if question.enabled
		]

	def submit(self, data, custom_fields_data=None) -> str:
		"""Record one enquiry against this form and return its name."""
		self.check_login()
		if self.is_closed:
			SubmissionsClosed.throw()
		values = frappe.parse_json(data) or {}
		if not isinstance(values, dict):
			frappe.throw(_("Could not read the submitted form. Please reload the page and try again."))
		enquiry = frappe.get_doc(self.build_doc_data(values))
		enquiry.enquiry_form = self.form.name
		enquiry.contact_email = enquiry.contact_email or session_user_email()
		enquiry.set(
			"additional_fields",
			CustomAnswers(self.form.custom_fields).rows(frappe.parse_json(custom_fields_data) or {}),
		)
		self.validate_tier_belongs_to_event(enquiry.tier)
		return enquiry.insert(ignore_permissions=True).name

	def validate_tier_belongs_to_event(self, tier):
		if not tier:
			return
		event, enabled = frappe.db.get_value("Sponsorship Tier", tier, ["event", "enabled"]) or (None, 0)
		if str(event) != str(self.event.name):
			frappe.throw(_("Select a sponsorship tier from this event."))
		if not enabled:
			frappe.throw(_("Select an available sponsorship tier from this event."))


def session_user_email() -> str | None:
	"""The signed-in user's address, to prefill the contact field. Guests have none."""
	if frappe.session.user == "Guest":
		return None
	return frappe.get_cached_value("User", frappe.session.user, "email")
