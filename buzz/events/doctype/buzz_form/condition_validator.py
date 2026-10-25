import frappe
from frappe import _
from frappe.utils import cstr

from buzz.api.forms.conditions import LIST_OPERATORS, OPERATORS, parse_conditions
from buzz.api.forms.fields import get_exclude_fields, get_renderable_fields

IS_VALUES = ("set", "not set")
VALUE_FIELDTYPES = frozenset({"Select", "Link"})


class ConditionValidator:
	"""Check a form's question conditions against the fields the form renders."""

	def __init__(self, form):
		self.form = form
		self.standard_fields = get_renderable_fields(
			form.form_doctype, get_exclude_fields(form.form_doctype, form.excluded_fields)
		)
		self.fieldnames_above = set()

	def validate(self):
		for question in self.form.questions:
			for conditions in (question.depends_on, question.mandatory_depends_on):
				for condition in self.read(question, conditions):
					self.validate_condition(question, condition)
			self.fieldnames_above.add(question.fieldname)

	def read(self, question, conditions) -> list:
		if not conditions:
			return []
		try:
			rows = parse_conditions(conditions)
		except ValueError:
			self.invalid(question, _("the condition is not valid JSON."))
		if not isinstance(rows, list) or any(not isinstance(row, list) or len(row) != 3 for row in rows):
			self.invalid(question, _("each condition must be [fieldname, operator, value]."))
		return rows

	def validate_condition(self, question, condition):
		fieldname, operator, expected = condition
		if operator not in OPERATORS:
			self.invalid(question, _("{0} is not a supported operator.").format(operator))
		if fieldname not in self.fieldnames_above and fieldname not in self.standard_fields:
			self.invalid(question, _("{0} is not a field above this question.").format(fieldname))
		if operator == "is" and expected not in IS_VALUES:
			self.invalid(question, _("Use 'set' or 'not set' with the 'is' operator."))
		if operator in LIST_OPERATORS and not isinstance(expected, list):
			self.invalid(question, _("Use a list of values with the '{0}' operator.").format(operator))
		if fieldname in self.standard_fields and operator != "is":
			self.validate_standard_values(question, self.standard_fields[fieldname], expected)

	def validate_standard_values(self, question, field, expected):
		if field.fieldtype not in VALUE_FIELDTYPES:
			return
		for value in expected if isinstance(expected, list) else [expected]:
			if field.fieldtype == "Select":
				self.validate_option(question, field, value)
			elif not self.link_value_exists(field, value):
				self.invalid(question, _("{0} does not exist.").format(value))

	def validate_option(self, question, field, value):
		label = field.label or field.fieldname
		if cstr(value) not in (field.options or "").splitlines():
			self.invalid(question, _("{0} is not an option of {1}.").format(value, label))

	def link_value_exists(self, field, value) -> bool:
		if not frappe.db.exists(field.options, value):
			return False
		if not frappe.get_meta(field.options).has_field("event"):
			return True
		event = frappe.db.get_value(field.options, value, "event")
		return cstr(event) == cstr(self.form.event)

	def invalid(self, question, message):
		frappe.throw(_("Condition on {0}: {1}").format(question.label, message))
