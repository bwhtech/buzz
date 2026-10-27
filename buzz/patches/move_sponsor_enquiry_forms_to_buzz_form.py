import frappe
from frappe import _
from frappe.utils import cstr

SOURCE_DOCTYPE = "Sponsor Enquiry Form"
TARGET_FORM_DOCTYPE = "Sponsorship Enquiry"
FORM_SETTINGS = (
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
	if not (frappe.db.exists("DocType", SOURCE_DOCTYPE) and frappe.db.table_exists(SOURCE_DOCTYPE)):
		return
	forms = SponsorFormMigration()
	forms.move()
	forms.delete_old_forms()


class SponsorFormMigration:
	def move(self):
		forms = self.build_forms()
		for form in forms:
			# A form outlives its event when enquiries keep it, so its event link may dangle.
			form.insert(
				ignore_permissions=True,
				set_name=form.flags.source_name,
				ignore_links=form.flags.get("orphaned"),
			)
			frappe.clear_document_cache("Buzz Event", form.event)

	def delete_old_forms(self):
		# A row left behind would lose its settings and questions with the doctype.
		if self.rows_to_move():
			frappe.throw(_("Some sponsorship forms could not be moved to Buzz Form."))
		frappe.delete_doc("DocType", SOURCE_DOCTYPE, ignore_missing=True, force=True)
		frappe.db.delete("Buzz Form Field", {"parenttype": SOURCE_DOCTYPE})

	def build_forms(self) -> list:
		# Event names come back as integers here and as strings on the form.
		events = {str(event) for event in frappe.get_all("Buzz Event", pluck="name")}
		forms = [self.build_form(row, str(row.event) not in events) for row in self.rows_to_move()]
		for form in forms:
			self.validate_form(form)
		return forms

	def validate_form(self, form):
		form.flags.migrating = True
		try:
			form.validate()
		except frappe.ValidationError as error:
			frappe.throw(
				_("Cannot move the sponsorship form of event {0}: {1}").format(form.event, cstr(error))
			)

	def rows_to_move(self) -> list:
		moved = set(frappe.get_all("Buzz Form", pluck="name"))
		return [
			row
			for row in frappe.get_all(SOURCE_DOCTYPE, fields=["name", "event", *FORM_SETTINGS])
			if row.name not in moved
		]

	def build_form(self, row, orphaned: bool):
		form = frappe.get_doc(
			{
				"doctype": "Buzz Form",
				"title": "Sponsorship enquiry",
				"form_doctype": TARGET_FORM_DOCTYPE,
				"event": row.event,
				**{fieldname: row.get(fieldname) for fieldname in FORM_SETTINGS},
			}
		)
		form.flags.source_name = row.name
		form.flags.orphaned = orphaned
		for question in self.questions_for(row.name):
			form.append("questions", {fieldname: question.get(fieldname) for fieldname in QUESTION_FIELDS})
		return form

	def questions_for(self, form_name: str) -> list:
		return frappe.get_all(
			"Buzz Form Field",
			filters={"parenttype": SOURCE_DOCTYPE, "parent": form_name},
			fields=list(QUESTION_FIELDS),
			order_by="idx",
		)
