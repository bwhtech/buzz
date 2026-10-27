import frappe
from frappe import _

from buzz.api.forms.fields import get_form_fields
from buzz.api.forms.services import CustomFormService
from buzz.events.doctype.buzz_form.form_types import ENQUIRY_FIELDS

ENQUIRY_DOCTYPE = "Sponsorship Enquiry"
SUBMISSION_METHOD = "buzz.api.sponsorships.submit_enquiry_form"


class SponsorFormService(CustomFormService):
	"""Serve the event's sponsorship Buzz Form through the shared custom form machinery."""

	def form_data(self):
		response = super().form_data()
		response.submission_method = SUBMISSION_METHOD
		return response

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

	def prepare_submission(self, enquiry):
		enquiry.enquiry_form = self.form.name
		enquiry.contact_email = enquiry.contact_email or session_user_email()
		self.validate_tier_belongs_to_event(enquiry.tier)

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
