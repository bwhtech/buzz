import frappe
from frappe import _
from frappe.utils import cstr

from buzz.events.doctype.buzz_form.form_types import SPONSORSHIP_FORM_DOCTYPE, form_type, usable_fieldname

SOURCE_DOCTYPE = "Buzz Event Form"
SETTINGS = (
	"route",
	"publish",
	"login_required",
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
	migration = EventFormMigration()
	forms = migration.build_forms()
	migration.insert_forms(forms)
	migration.delete_source()


class EventFormMigration:
	"""Copy every Buzz Event Form row and its questions into a Buzz Form, then drop the old table.

	Nothing is deleted before every form has validated and been written: a failed migrate is
	rolled back by Frappe, but a re-run must still find its source rows to be idempotent.
	"""

	def build_forms(self) -> list:
		forms = []
		doctypes = {}
		for row in self.pending_rows():
			route = (cstr(row.parent), (row.route or "").lower())
			# Repeated rows of one form are that form; two different forms on one route would collide.
			if doctypes.setdefault(route, row.form_doctype) != row.form_doctype:
				frappe.throw(
					_("Two custom forms of event {0} use the route {1}.").format(row.parent, row.route)
				)
			forms.append(self.build_form(row))
		for form in forms:
			self.validate_form(form)
		return forms

	def build_form(self, row):
		form = frappe.get_doc(
			{
				"doctype": "Buzz Form",
				"title": row.form_doctype,
				"event": row.parent,
				"form_doctype": row.form_doctype,
				**{fieldname: row.get(fieldname) for fieldname in SETTINGS},
			}
		)
		form.flags.migrating = True
		for question in self.questions_of(row):
			form.append("questions", question)
		return form

	def questions_of(self, row) -> list[dict]:
		questions = frappe.get_all(
			"Buzz Custom Field",
			filters={
				"event": row.parent,
				"applied_to": "Custom Form",
				"custom_form_doctype": row.form_doctype,
			},
			fields=list(QUESTION_FIELDS),
			order_by="order asc, creation asc",
		)
		if questions and not frappe.get_meta(row.form_doctype).has_field("additional_fields"):
			# The old code showed no question on such a doctype; keeping them would fail validate.
			print(f"Skipping {len(questions)} questions: {row.form_doctype} has no additional_fields.")
			return []
		return self.name_questions(questions, form_type(row.form_doctype).reserved_fieldnames)

	def name_questions(self, questions: list, reserved: frozenset) -> list[dict]:
		taken = set()
		rows = []
		for question in questions:
			row = {fieldname: question.get(fieldname) for fieldname in QUESTION_FIELDS}
			row["fieldname"] = usable_fieldname(row["fieldname"] or row["label"], taken, reserved)
			rows.append(row)
		return rows

	def validate_form(self, form):
		try:
			form.validate()
		except frappe.ValidationError as error:
			frappe.throw(_("Cannot move the custom form of event {0}: {1}").format(form.event, error))

	def insert_forms(self, forms: list):
		for form in forms:
			form.insert(ignore_permissions=True)
			frappe.clear_document_cache("Buzz Event", form.event)

	def delete_source(self):
		# Every row left pending is a row whose settings would go with the doctype.
		if self.pending_rows():
			frappe.throw(_("Some custom forms could not be moved to Buzz Form."))
		frappe.db.delete(SOURCE_DOCTYPE, {"parenttype": "Buzz Event"})
		frappe.delete_doc("DocType", SOURCE_DOCTYPE, ignore_missing=True, force=True)

	def pending_rows(self) -> list:
		"""Form rows with no Buzz Form yet, oldest first inside an event."""
		existing = frappe.get_all("Buzz Form", fields=["event", "form_doctype", "route"])
		moved = {(cstr(form.event), form.form_doctype, (form.route or "").lower()) for form in existing}
		sponsored = {cstr(form.event) for form in existing if form.form_doctype == SPONSORSHIP_FORM_DOCTYPE}
		rows = frappe.get_all(
			SOURCE_DOCTYPE,
			filters={"parenttype": "Buzz Event"},
			fields=["parent", "form_doctype", *SETTINGS],
			order_by="parent, idx",
		)
		pending = []
		for row in rows:
			if row.form_doctype == SPONSORSHIP_FORM_DOCTYPE and cstr(row.parent) in sponsored:
				# A legacy sponsorship row whose form the sponsorship port already made.
				continue
			key = (cstr(row.parent), row.form_doctype, (row.route or "").lower())
			if key in moved:
				# A repeated row is the same form, once; a Buzz Form already there is the same too.
				continue
			moved.add(key)
			pending.append(row)
		return pending
