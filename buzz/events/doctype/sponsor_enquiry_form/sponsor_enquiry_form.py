import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from buzz.api.forms.fields import parse_excluded_fields, validate_excluded_fields

ENQUIRY_FIELDS = frozenset(
	{"company_name", "company_logo", "website", "tier", "country", "phone", "contact_email"}
)


class SponsorEnquiryForm(Document):
	def validate(self):
		self.validate_event_is_unchanged()
		self.validate_route()
		validate_excluded_fields("Sponsorship Enquiry", self.excluded_fields)
		if self.allow_guest_submissions and "contact_email" in (
			parse_excluded_fields(self.excluded_fields) or set()
		):
			frappe.throw(_("Contact Email cannot be hidden when guest submissions are enabled."))
		self.validate_questions()
		if (
			self.publish
			and not self.flags.migrating_sponsorship
			and not frappe.db.get_value("Buzz Event", self.event, "is_published")
		):
			frappe.throw(_("Publish the event before opening its sponsorship form."))

	def validate_event_is_unchanged(self):
		before = self.get_doc_before_save()
		if before and cstr(before.event) != cstr(self.event):
			frappe.throw(
				_("A sponsorship form cannot be moved to another event."), frappe.CannotChangeConstantError
			)

	def validate_route(self):
		if not self.route or not re.fullmatch(r"[a-zA-Z0-9_-]+", self.route):
			frappe.throw(_("Use only letters, numbers, hyphens and underscores in the form route."))
		clashing = frappe.get_all(
			"Buzz Event Form",
			filters={"parent": self.event, "parenttype": "Buzz Event", "route": self.route},
			pluck="name",
		)
		if any(name != self.flags.legacy_form_row for name in clashing):
			frappe.throw(_("This route is already used by another event form."))

	def validate_questions(self):
		used_fieldnames = set()
		before_save = self.get_doc_before_save()
		saved_fieldnames = (
			{question.name: question.fieldname for question in before_save.custom_fields}
			if before_save
			else {}
		)
		for question in self.custom_fields:
			question.fieldname = question.fieldname or frappe.scrub(question.label or "")
			if not re.fullmatch(r"[a-z][a-z0-9_]*", question.fieldname):
				frappe.throw(
					_(
						"Question fieldnames must start with a letter and contain lowercase letters, numbers or underscores."
					)
				)
			if question.fieldname in used_fieldnames or question.fieldname in ENQUIRY_FIELDS:
				frappe.throw(_("Duplicate or reserved question fieldname: {0}").format(question.fieldname))
			if saved_fieldnames.get(question.name) not in (None, question.fieldname):
				frappe.throw(_("A saved question's fieldname cannot be changed. Add a new question instead."))
			used_fieldnames.add(question.fieldname)


def create_for_event(event: str) -> Document:
	return frappe.get_doc({"doctype": "Sponsor Enquiry Form", "event": event}).insert(ignore_permissions=True)
