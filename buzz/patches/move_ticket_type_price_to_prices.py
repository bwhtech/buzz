import frappe


def execute():
	# The dropped price and currency columns stay in the table after the model sync.
	if not frappe.db.has_column("Event Ticket Type", "price"):
		return

	ticket_type = frappe.qb.DocType("Event Ticket Type")
	rows = (
		frappe.qb.from_(ticket_type)
		.select(ticket_type.name, ticket_type.price, ticket_type.currency)
		.run(as_dict=True)
	)
	for row in rows:
		if frappe.db.exists("Buzz Price", {"parenttype": "Event Ticket Type", "parent": str(row.name)}):
			continue
		frappe.get_doc(
			{
				"doctype": "Buzz Price",
				"parenttype": "Event Ticket Type",
				"parent": str(row.name),
				"parentfield": "prices",
				"idx": 1,
				"currency": row.currency or "INR",
				"price": row.price or 0,
			}
		).db_insert()
