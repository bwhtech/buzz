import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from buzz.api.forms.fields import validate_excluded_fields

ENQUIRY_FIELDS = frozenset(
	{"company_name", "company_logo", "website", "tier", "country", "phone", "contact_email"}
)


class SponsorEnquiryForm(Document):
	def validate(self):
		self.validate_event_is_unchanged()
		self.validate_route()
		validate_excluded_fields("Sponsorship Enquiry", self.excluded_fields)
		if self.allow_guest_submissions and "contact_email" in (self.excluded_fields or "").replace(
			" ", ""
		).split(","):
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
		rows = frappe.get_all(
			"Buzz Event Form",
			filters={"parent": self.event, "parenttype": "Buzz Event"},
			fields=["name", "route"],
		)
		if any(
			row.route.lower() == self.route.lower() and row.name != self.flags.legacy_form_row for row in rows
		):
			frappe.throw(_("This route is already used by another event form."))

	def validate_questions(self):
		seen = set()
		before = self.get_doc_before_save()
		previous = {row.name: row.fieldname for row in before.custom_fields} if before else {}
		for row in self.custom_fields:
			row.fieldname = row.fieldname or frappe.scrub(row.label or "")
			if not re.fullmatch(r"[a-z][a-z0-9_]*", row.fieldname):
				frappe.throw(
					_(
						"Question fieldnames must start with a letter and contain lowercase letters, numbers or underscores."
					)
				)
			if row.fieldname in seen or row.fieldname in ENQUIRY_FIELDS:
				frappe.throw(_("Duplicate or reserved question fieldname: {0}").format(row.fieldname))
			if previous.get(row.name) and previous[row.name] != row.fieldname:
				frappe.throw(_("A saved question's fieldname cannot be changed. Add a new question instead."))
			seen.add(row.fieldname)


def create_for_event(event: str) -> Document:
	return frappe.get_doc({"doctype": "Sponsor Enquiry Form", "event": event}).insert(ignore_permissions=True)
