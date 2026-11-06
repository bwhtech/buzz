import frappe
from frappe import _
from frappe.utils import cstr

from buzz.api.forms.conditions import ACTIONS, LIST_OPERATORS, OPERATORS, parse_rules
from buzz.api.forms.fields import get_renderable_fields, system_exclude_fields

IS_OPERATOR_VALUES = ("set", "not set")
VALIDATED_FIELDTYPES = frozenset({"Select", "Link"})


class ConditionValidator:
	"""Check a form's logic rules against the fields the form renders.

	A condition names a field of the form's doctype or a question above every question the
	rule acts on, so one pass down the form decides each question.
	"""

	def __init__(self, form):
		self.form = form
		# Every renderable field, page or not: attendee questions name the ticket type.
		self.standard_fields = get_renderable_fields(
			form.form_doctype, system_exclude_fields(form.form_doctype)
		)
		# A step is never a rule's target: hiding one would leave the form without its page.
		self.positions = {
			question.fieldname: index
			for index, question in enumerate(form.questions)
			if not question.is_standard and question.fieldtype != "Page Break"
		}

	def validate(self):
		rules = self.parse()
		for rule in rules:
			self.validate_rule(rule)
		self.form.logic_rules = frappe.as_json(rules, indent=None) if rules else None

	def parse(self) -> list:
		try:
			rules = parse_rules(self.form.logic_rules)
		except ValueError:
			self.throw(_("the rules are not valid JSON."))
		if not isinstance(rules, list) or any(not isinstance(rule, dict) for rule in rules):
			self.throw(_("each rule must be an object with conditions and actions."))
		return rules

	def validate_rule(self, rule: dict):
		if rule.get("match", "all") not in ("all", "any"):
			self.throw(_("match must be 'all' or 'any'."))
		conditions, actions = rule.get("conditions") or [], rule.get("actions") or []
		if not conditions or not actions:
			self.throw(_("every rule needs a condition and an action."))
		first_target = min(self.validate_action(action) for action in actions)
		for condition in conditions:
			self.validate_condition(condition, first_target)

	def validate_action(self, action) -> int:
		if not isinstance(action, list) or len(action) != 2 or action[0] not in ACTIONS:
			self.throw(_("each action must be [show, hide or require, question]."))
		if action[1] not in self.positions:
			self.throw(_("{0} is not a question on this form.").format(action[1]))
		return self.positions[action[1]]

	def validate_condition(self, condition, first_target: int):
		if not isinstance(condition, list) or len(condition) != 3:
			self.throw(_("each condition must be [fieldname, operator, value]."))
		fieldname, operator, expected = condition
		if operator not in OPERATORS:
			self.throw(_("{0} is not a supported operator.").format(operator))
		if (
			fieldname not in self.standard_fields
			and self.positions.get(fieldname, first_target) >= first_target
		):
			self.throw(_("{0} is not a field above the questions this rule changes.").format(fieldname))
		if operator == "is" and expected not in IS_OPERATOR_VALUES:
			self.throw(_("Use 'set' or 'not set' with the 'is' operator."))
		if operator in LIST_OPERATORS and not isinstance(expected, list):
			self.throw(_("Use a list of values with the '{0}' operator.").format(operator))
		if fieldname in self.standard_fields and operator != "is":
			self.validate_standard_values(self.standard_fields[fieldname], expected)

	def drop_link_conditions(self):
		"""A Link value names a record of one event, so a condition copied to another cannot hold."""
		kept = []
		for rule in parse_rules(self.form.logic_rules):
			rule["conditions"] = [
				condition
				for condition in rule.get("conditions") or []
				if getattr(self.standard_fields.get(condition[0]), "fieldtype", None) != "Link"
			]
			if rule["conditions"]:
				kept.append(rule)
		self.form.logic_rules = frappe.as_json(kept, indent=None) if kept else None

	def validate_standard_values(self, field, expected):
		if field.fieldtype not in VALIDATED_FIELDTYPES:
			return
		for value in expected if isinstance(expected, list) else [expected]:
			if field.fieldtype == "Select":
				self.validate_option(field, value)
			elif not self.link_value_exists(field, value):
				self.throw(_("{0} does not exist.").format(value))

	def validate_option(self, field, value):
		if cstr(value) not in (field.options or "").splitlines():
			self.throw(_("{0} is not an option of {1}.").format(value, field.label or field.fieldname))

	def link_value_exists(self, field, value) -> bool:
		if not frappe.db.exists(field.options, value):
			return False
		if not frappe.get_meta(field.options).has_field("event"):
			return True
		event = frappe.db.get_value(field.options, value, "event")
		return cstr(event) == cstr(self.form.event)

	def throw(self, message):
		frappe.throw(_("Logic rule: {0}").format(message))
