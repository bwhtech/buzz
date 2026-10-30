from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cstr

from buzz.events.doctype.buzz_form.form_types import (
	ATTENDEE_FORM_DOCTYPE,
	ATTENDEE_ROUTE,
	REGISTRATION_FORM_DOCTYPE,
	REGISTRATION_ROUTE,
	unique_fieldname,
)

# Each legacy `applied_to` and the registration form that now asks it.
REGISTRATION_FORMS = {
	"Booking": (REGISTRATION_FORM_DOCTYPE, REGISTRATION_ROUTE, "Registration"),
	"Ticket": (ATTENDEE_FORM_DOCTYPE, ATTENDEE_ROUTE, "Attendee details"),
}
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
	migration = RegistrationMigration()
	forms = migration.build_forms()
	for form in forms:
		if form.is_new():
			form.insert(ignore_permissions=True)
		else:
			form.save(ignore_permissions=True)
		frappe.clear_document_cache("Buzz Event", form.event)


class RegistrationMigration:
	"""Copy each event's booking questions into its registration Buzz Form, and its ticket
	questions into its attendee Buzz Form.

	The Buzz Custom Field rows stay where they are; a later patch removes them. A form that
	already has questions is left alone, so a second run changes nothing.
	"""

	def build_forms(self) -> list:
		questions = self.legacy_questions()
		forms = []
		for event in frappe.get_all("Buzz Event", pluck="name"):
			for applied_to, form_settings in REGISTRATION_FORMS.items():
				rows = questions[(cstr(event), applied_to)]
				if form := self.build_form(cstr(event), form_settings, rows):
					forms.append(form)
		return forms

	def build_form(self, event: str, form_settings: tuple, legacy_rows: list):
		form = self.registration_form(event, *form_settings)
		if form.questions or (not legacy_rows and not form.is_new()):
			return None
		for row in self.question_rows(legacy_rows):
			form.append("questions", row)
		self.validate_form(form)
		return form

	def registration_form(self, event: str, form_doctype: str, route: str, title: str):
		name = frappe.db.get_value("Buzz Form", {"event": event, "form_doctype": form_doctype}, "name")
		if name:
			return frappe.get_doc("Buzz Form", name)
		# new_doc, not get_doc: only new_doc marks the form new, and build_form skips a form
		# that is not new and has nothing to move.
		form = frappe.new_doc(
			"Buzz Form",
			title=title,
			event=event,
			form_doctype=form_doctype,
			route=route,
			# Registration was open before this form existed; the attendee form has no switch.
			publish=int(form_doctype == REGISTRATION_FORM_DOCTYPE),
		)
		if form_doctype == REGISTRATION_FORM_DOCTYPE:
			form.auto_close_at = self.legacy_cutoff(event)
		form.flags.migrating = True
		return form

	def legacy_cutoff(self, event: str):
		"""move_registration_close_to_buzz_form skips an event with no form, so a form made
		here takes the cutoff itself."""
		if not frappe.db.has_column("Buzz Event", "registrations_close_at"):
			return None
		rows = frappe.db.sql("select registrations_close_at from `tabBuzz Event` where name = %s", event)
		return rows[0][0]

	def legacy_questions(self) -> dict[tuple, list]:
		rows = frappe.get_all(
			"Buzz Custom Field",
			filters={"applied_to": ["in", list(REGISTRATION_FORMS)]},
			fields=["event", "applied_to", *QUESTION_FIELDS],
			order_by="order asc, creation asc",
		)
		grouped = defaultdict(list)
		for row in rows:
			grouped[(cstr(row.event), row.applied_to)].append(row)
		return grouped

	def question_rows(self, legacy_rows: list) -> list[dict]:
		taken = set()
		rows = []
		for legacy in legacy_rows:
			row = {name: legacy.get(name) for name in QUESTION_FIELDS}
			row["fieldname"] = unique_fieldname(row["fieldname"] or row["label"], taken, frozenset())
			rows.append(row)
		return rows

	def validate_form(self, form):
		try:
			form.validate()
		except frappe.ValidationError as error:
			frappe.throw(
				_("Cannot move the registration questions of event {0}: {1}").format(form.event, cstr(error))
			)
