import frappe
from frappe import _

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
		for question in questions:
			form.append("custom_fields", {key: question.get(key) for key in QUESTION_FIELDS})
		form.flags.migrating_sponsorship = True
		form.validate()
		return form, legacy, questions
