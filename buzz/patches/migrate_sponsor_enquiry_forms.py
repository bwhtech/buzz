import re

import frappe
from frappe import _
from frappe.utils import scrub

from buzz.events.doctype.sponsor_enquiry_form.sponsor_enquiry_form import ENQUIRY_FIELDS

SETTINGS = (
	"route",
	"publish",
	"auto_close_at",
	"excluded_fields",
	"success_title",
	"success_message",
	"closed_title",
	"closed_message",
)
QUESTION_FIELDS = (
	"enabled",
	"label",
	"fieldname",
	"fieldtype",
	"options",
	"mandatory",
	"placeholder",
	"default_value",
)


def execute():
	SponsorFormMigration().run()


class SponsorFormMigration:
	def run(self):
		pending = self.prepare()
		for form, legacy_row, questions in pending:
			form.insert(ignore_permissions=True)
			if legacy_row:
				frappe.db.delete("Buzz Event Form", {"name": legacy_row.name})
			for question in questions:
				frappe.db.set_value("Buzz Custom Field", question.name, "enabled", 0, update_modified=False)
			frappe.clear_document_cache("Buzz Event", form.event)
		if frappe.db.exists("Web Form", "apply-for-sponsorship"):
			frappe.db.set_value("Web Form", "apply-for-sponsorship", "published", 0)
			frappe.clear_document_cache("Web Form", "apply-for-sponsorship")

	def prepare(self):
		pending = []
		for event in frappe.get_all("Buzz Event", pluck="name", order_by="name"):
			legacy = frappe.get_all(
				"Buzz Event Form",
				filters={"parent": event, "parenttype": "Buzz Event", "form_doctype": "Sponsorship Enquiry"},
				fields=["name", "login_required", *SETTINGS],
			)
			existing = frappe.db.exists("Sponsor Enquiry Form", {"event": event})
			if len(legacy) > 1 or (existing and legacy):
				frappe.throw(
					_("Resolve conflicting sponsorship forms for event {0} before migrating.").format(event)
				)
			if existing:
				continue
			pending.append(self.prepare_event(event, legacy[0] if legacy else None))
		return pending

	def prepare_event(self, event, legacy):
		questions = frappe.get_all(
			"Buzz Custom Field",
			filters={
				"event": event,
				"applied_to": "Custom Form",
				"custom_form_doctype": "Sponsorship Enquiry",
			},
			fields=["name", *QUESTION_FIELDS],
			order_by="order asc, creation asc",
		)
		form = frappe.get_doc(
			{"doctype": "Sponsor Enquiry Form", "event": event, "route": "enquire-sponsorship"}
		)
		if legacy:
			form.update({key: legacy.get(key) for key in SETTINGS})
			form.allow_guest_submissions = not legacy.login_required
			form.flags.legacy_form_row = legacy.name
		taken = set()
		for question in questions:
			row = {key: question.get(key) for key in QUESTION_FIELDS}
			row["fieldname"] = self.usable_fieldname(row, taken)
			form.append("custom_fields", row)
		form.flags.migrating_sponsorship = True
		form.validate()
		return form, legacy, questions

	def usable_fieldname(self, question, taken):
		"""Legacy questions were never held to the new key rules, so reshape rather than refuse.

		A site whose sponsorship form asks for a "Website" is ordinary, and failing the whole
		migrate over it strands every other event. Old answers keep their own fieldname copy,
		so a rename here only affects what arrives next.
		"""
		name = re.sub(r"[^a-z0-9_]", "_", scrub(question.get("fieldname") or question.get("label") or ""))
		if not name[:1].isalpha():
			name = f"question_{name}"
		candidate, suffix = name, 2
		while candidate in taken or candidate in ENQUIRY_FIELDS:
			candidate, suffix = f"{name}_{suffix}", suffix + 1
		taken.add(candidate)
		return candidate
