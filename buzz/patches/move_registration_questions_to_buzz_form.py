from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cstr

from buzz.events.doctype.buzz_form.form_types import (
	ASKED_PER_BY_APPLIED_TO,
	REGISTRATION_FORM_DOCTYPE,
	REGISTRATION_ROUTE,
	usable_fieldname,
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
	migration = RegistrationMigration()
	forms = migration.build_forms()
	for form in forms:
		if form.is_new():
			form.insert(ignore_permissions=True)
		else:
			form.save(ignore_permissions=True)
		frappe.clear_document_cache("Buzz Event", form.event)


class RegistrationMigration:
	"""Copy each event's booking and ticket questions into its registration Buzz Form.

	The Buzz Custom Field rows stay where they are; a later patch removes them. An event whose
	registration form already has questions is left alone, so a second run changes nothing.
	"""

	def build_forms(self) -> list:
		questions = self.legacy_questions()
		forms = []
		for event in frappe.get_all("Buzz Event", pluck="name"):
			form = self.registration_form(cstr(event))
			if form.questions:
				continue
			rows = self.question_rows(questions.get(cstr(event), []))
			if not rows and not form.is_new():
				continue
			for row in rows:
				form.append("questions", row)
			self.validate_form(form)
			forms.append(form)
		return forms

	def registration_form(self, event: str):
		name = frappe.db.get_value(
			"Buzz Form", {"event": event, "form_doctype": REGISTRATION_FORM_DOCTYPE}, "name"
		)
		if name:
			return frappe.get_doc("Buzz Form", name)
		form = frappe.get_doc(
			{
				"doctype": "Buzz Form",
				"title": "Registration",
				"event": event,
				"form_doctype": REGISTRATION_FORM_DOCTYPE,
				"route": REGISTRATION_ROUTE,
				"publish": 1,
			}
		)
		form.flags.migrating = True
		return form

	def legacy_questions(self) -> dict[str, list]:
		rows = frappe.get_all(
			"Buzz Custom Field",
			filters={"applied_to": ["in", list(ASKED_PER_BY_APPLIED_TO)]},
			fields=["event", "applied_to", *QUESTION_FIELDS],
			order_by="order asc, creation asc",
		)
		grouped = defaultdict(list)
		for row in rows:
			grouped[cstr(row.event)].append(row)
		return grouped

	def question_rows(self, legacy_rows: list) -> list[dict]:
		taken = defaultdict(set)
		rows = []
		for legacy in legacy_rows:
			asked_per = ASKED_PER_BY_APPLIED_TO[legacy.applied_to]
			row = {name: legacy.get(name) for name in QUESTION_FIELDS}
			row["fieldname"] = usable_fieldname(
				row["fieldname"] or row["label"], taken[asked_per], frozenset()
			)
			rows.append({**row, "asked_per": asked_per})
		return rows

	def validate_form(self, form):
		try:
			form.validate()
		except frappe.ValidationError as error:
			frappe.throw(
				_("Cannot move the registration questions of event {0}: {1}").format(form.event, error)
			)
