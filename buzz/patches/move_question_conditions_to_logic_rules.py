from collections import defaultdict

import frappe


def execute():
	"""Each question's show and required conditions become rules on its form."""
	# Sites that skipped straight past the columns never had conditions to move.
	if not frappe.db.has_column("Buzz Form Field", "depends_on"):
		return
	rules_by_form = defaultdict(list)
	for form, fieldname, depends_on, mandatory_depends_on in question_conditions():
		for action, conditions in (("show", depends_on), ("require", mandatory_depends_on)):
			if conditions := frappe.parse_json(conditions) if conditions else None:
				rules_by_form[form].append(
					{"match": "all", "conditions": conditions, "actions": [[action, fieldname]]}
				)
	for form, rules in rules_by_form.items():
		# Skip a form already moved, so a second run changes nothing.
		if not frappe.db.get_value("Buzz Form", form, "logic_rules"):
			frappe.db.set_value(
				"Buzz Form", form, "logic_rules", frappe.as_json(rules, indent=None), update_modified=False
			)


def question_conditions() -> list:
	field = frappe.qb.DocType("Buzz Form Field")
	return (
		frappe.qb.from_(field)
		.select(field.parent, field.fieldname, field.depends_on, field.mandatory_depends_on)
		.where(field.parenttype == "Buzz Form")
		.where(field.depends_on.isnotnull() | field.mandatory_depends_on.isnotnull())
		.orderby(field.parent)
		.orderby(field.idx)
		.run()
	)
