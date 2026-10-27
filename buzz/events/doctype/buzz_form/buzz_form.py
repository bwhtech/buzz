import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from buzz.api.forms.fields import validate_excluded_fields
from buzz.events.doctype.buzz_form.condition_validator import ConditionValidator
from buzz.events.doctype.buzz_form.form_types import form_type, unique_fieldname

ROUTE_PATTERN = r"[a-zA-Z0-9_-]+"
FIELDNAME_PATTERN = r"[a-z][a-z0-9_]*"


class BuzzForm(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from buzz.events.doctype.buzz_form_field.buzz_form_field import BuzzFormField

		auto_close_at: DF.Datetime | None
		closed_message: DF.SmallText | None
		closed_title: DF.Data | None
		description: DF.SmallText | None
		event: DF.Link
		excluded_fields: DF.SmallText | None
		form_doctype: DF.Link
		login_required: DF.Check
		publish: DF.Check
		questions: DF.Table[BuzzFormField]
		route: DF.Data
		submit_label: DF.Data | None
		success_message: DF.MarkdownEditor | None
		success_title: DF.Data | None
		title: DF.Data
	# end: auto-generated types

	@property
	def is_closed(self) -> bool:
		return form_type(self.form_doctype).is_closed(self)

	@frappe.whitelist(methods=["POST"])
	def set_closed(self, closed: bool) -> bool:
		if closed:
			form_type(self.form_doctype).close(self)
		else:
			form_type(self.form_doctype).open(self)
		self.save()
		return self.is_closed

	def validate(self):
		self.validate_unchanged_fields()
		self.validate_route()
		validate_excluded_fields(self.form_doctype, self.excluded_fields)
		self.validate_questions()
		self.validate_conditions()
		self.validate_event_is_published()
		self.validate_answers_field()
		form_type(self.form_doctype).validate(self)

	def validate_unchanged_fields(self):
		# `event` carries no `set_only_once`: Frappe compares its saved string with the
		# integer it loads, and refuses every save of an event-named form.
		before = self.get_doc_before_save()
		if not before:
			return
		if cstr(before.event) != cstr(self.event):
			frappe.throw(_("A form cannot be moved to another event."), frappe.CannotChangeConstantError)
		if cstr(before.form_doctype) != cstr(self.form_doctype):
			frappe.throw(_("A form's type cannot be changed."), frappe.CannotChangeConstantError)

	def validate_route(self):
		if not self.route or not re.fullmatch(ROUTE_PATTERN, self.route):
			frappe.throw(_("Use only letters, numbers, hyphens and underscores in the form route."))
		if self.route_is_taken():
			frappe.throw(_("This route is already used by another form of this event."))

	def route_is_taken(self) -> bool:
		taken = frappe.get_all(
			"Buzz Form", filters={"event": self.event, "name": ["!=", self.name or ""]}, pluck="route"
		)
		return any(route and route.lower() == self.route.lower() for route in taken)

	def validate_questions(self):
		reserved = form_type(self.form_doctype).reserved_fieldnames
		self.set_missing_fieldnames(reserved)
		used_fieldnames = set()
		saved_fieldnames = self.saved_question_fieldnames()
		for question in self.questions:
			if not re.fullmatch(FIELDNAME_PATTERN, question.fieldname):
				frappe.throw(
					_(
						"Question fieldnames must start with a letter and contain lowercase letters, numbers or underscores."
					)
				)
			if question.fieldname in used_fieldnames or question.fieldname in reserved:
				frappe.throw(_("Duplicate or reserved question fieldname: {0}").format(question.fieldname))
			if saved_fieldnames.get(question.name) not in (None, question.fieldname):
				frappe.throw(_("A saved question's fieldname cannot be changed. Add a new question instead."))
			used_fieldnames.add(question.fieldname)

	def set_missing_fieldnames(self, reserved: frozenset):
		taken = {question.fieldname for question in self.questions if question.fieldname}
		for question in self.questions:
			if not question.fieldname:
				question.fieldname = unique_fieldname(question.label or question.fieldtype, taken, reserved)

	def saved_question_fieldnames(self) -> dict[str, str]:
		before = self.get_doc_before_save()
		return {question.name: question.fieldname for question in before.questions} if before else {}

	def validate_conditions(self):
		ConditionValidator(self).validate()

	def validate_event_is_published(self):
		if self.flags.migrating or not form_type(self.form_doctype).has_page or self.is_closed:
			return
		if not frappe.db.get_value("Buzz Event", self.event, "is_published"):
			frappe.throw(_("Publish the event before opening its form."))

	def validate_answers_field(self):
		answers_field = form_type(self.form_doctype).answers_field
		if self.questions and not frappe.get_meta(self.form_doctype).has_field(answers_field):
			frappe.throw(_("{0} has no field to store answers in.").format(self.form_doctype))
