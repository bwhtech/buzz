import frappe
from frappe.utils import compare, flt

OPERATORS = frozenset({"=", "!=", "in", "not in", ">", "<", ">=", "<=", "is"})

LIST_OPERATORS = frozenset({"in", "not in"})

NUMBER_OPERATORS = frozenset({">", "<", ">=", "<="})


def all_conditions_match(conditions, values: dict) -> bool:
	"""Every [fieldname, operator, value] triple holds. Empty conditions always match."""
	return all(condition_matches(condition, values) for condition in parse_conditions(conditions) or [])


def parse_conditions(conditions) -> list | None:
	"""Conditions are JSON in the database and a list once read by the desk."""
	return frappe.parse_json(conditions) or None


def is_shown(question, values: dict) -> bool:
	return all_conditions_match(question.depends_on, values)


def is_required(question, values: dict) -> bool:
	"""A hidden question is never required, whatever its own flags say."""
	if not is_shown(question, values):
		return False
	required_conditions = parse_conditions(question.mandatory_depends_on)
	return bool(question.mandatory) or (
		bool(required_conditions) and all_conditions_match(required_conditions, values)
	)


def condition_matches(condition, values: dict) -> bool:
	fieldname, operator, expected = condition
	value = values.get(fieldname)
	# A Multi Select answer is a list: it is in the expected values when any of them is.
	if isinstance(value, list) and operator in LIST_OPERATORS:
		found = any(item in expected for item in value)
		return found if operator == "in" else not found
	if operator in NUMBER_OPERATORS:
		return compare(flt(value), operator, flt(expected))
	return compare(value, operator, expected)
