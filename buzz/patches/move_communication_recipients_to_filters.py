import json

import frappe

OLD_FILTERS = {"ticket_types": "ticket_type", "statuses": "status"}


def execute():
	columns = [column for column in OLD_FILTERS if frappe.db.has_column("Event Communication", column)]
	if not columns:
		return
	# Query builder: the columns are gone from the doctype, so get_all would reject them.
	table = frappe.qb.DocType("Event Communication")
	rows = frappe.qb.from_(table).select(table.name, *(table[column] for column in columns)).run(as_dict=True)
	for row in rows:
		conditions = [condition_of(OLD_FILTERS[column], row[column]) for column in columns]
		conditions = [condition for condition in conditions if condition]
		if conditions:
			frappe.db.set_value(
				"Event Communication", row.name, "filters", json.dumps(conditions), update_modified=False
			)


def condition_of(field: str, comma_joined: str | None) -> list | None:
	values = [value.strip() for value in (comma_joined or "").split(",") if value.strip()]
	return [field, "in", values] if values else None
