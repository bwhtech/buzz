import frappe
from frappe.utils import compare, cstr, flt

OPERATORS = frozenset({"=", "!=", "in", "not in", ">", "<", ">=", "<=", "is", "like"})

LIST_OPERATORS = frozenset({"in", "not in"})

NUMBER_OPERATORS = frozenset({">", "<", ">=", "<="})

# What a rule may do to the questions it names.
ACTIONS = frozenset({"show", "hide", "require"})


def parse_rules(rules) -> list[dict]:
	"""Rules are JSON in the database and a list once read by the desk."""
	return frappe.parse_json(rules) or []


def condition_matches(condition, values: dict) -> bool:
	fieldname, operator, expected = condition
	value = values.get(fieldname)
	# A Multi Select answer is a list: it is in the expected values when any of them is.
	if isinstance(value, list) and operator in LIST_OPERATORS:
		found = any(item in expected for item in value)
		return found if operator == "in" else not found
	if operator in NUMBER_OPERATORS:
		return compare(flt(value), operator, flt(expected))
	if operator == "like":
		return cstr(expected).lower() in cstr(value).lower()
	return compare(value, operator, expected)


def rule_matches(rule: dict, values: dict) -> bool:
	"""A rule with no conditions never fires; `any` needs one condition to hold, `all` every one."""
	results = [condition_matches(condition, values) for condition in rule.get("conditions") or []]
	if not results:
		return False
	return any(results) if rule.get("match") == "any" else all(results)


class FormLogic:
	"""What a form's rules make of each question, given the values answered so far."""

	def __init__(self, rules):
		self.rules = parse_rules(rules)

	def fires(self, action: str, fieldname: str, values: dict) -> list[bool]:
		return [
			rule_matches(rule, values)
			for rule in self.rules
			if [action, fieldname] in (rule.get("actions") or [])
		]

	def is_shown(self, question, values: dict) -> bool:
		"""Shown unless a show rule exists and none fires, or a hide rule fires."""
		shows = self.fires("show", question.fieldname, values)
		return (not shows or any(shows)) and not any(self.fires("hide", question.fieldname, values))

	def is_required(self, question, values: dict) -> bool:
		"""A hidden question is never required, whatever its own flags say."""
		if not self.is_shown(question, values):
			return False
		return bool(question.mandatory) or any(self.fires("require", question.fieldname, values))
