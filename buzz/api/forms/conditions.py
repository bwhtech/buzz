import frappe
from frappe.utils import compare

OPERATORS = frozenset({"=", "!=", "in", "not in", ">", "<", ">=", "<=", "is"})

LIST_OPERATORS = frozenset({"in", "not in"})


def matches(conditions, values: dict) -> bool:
	"""Every [fieldname, operator, value] triple holds. Empty conditions always match."""
	return all(holds(condition, values) for condition in parse_conditions(conditions) or [])


def parse_conditions(conditions) -> list | None:
	"""Conditions are JSON in the database and a list once read by the desk."""
	return frappe.parse_json(conditions) or None


def is_shown(question, values: dict) -> bool:
	return matches(question.depends_on, values)


def is_required(question, values: dict) -> bool:
	"""A hidden question is never required, whatever its own flags say."""
	if not is_shown(question, values):
		return False
	required_when = parse_conditions(question.mandatory_depends_on)
	return bool(question.mandatory) or (bool(required_when) and matches(required_when, values))


def holds(condition, values: dict) -> bool:
	fieldname, operator, expected = condition
	value = values.get(fieldname)
	# A Multi Select answer is a list: it is in the expected values when any of them is.
	if isinstance(value, list) and operator in LIST_OPERATORS:
		found = any(item in expected for item in value)
		return found if operator == "in" else not found
	return compare(value, operator, expected)
