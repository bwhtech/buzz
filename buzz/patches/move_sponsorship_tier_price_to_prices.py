import frappe


def execute():
	# The dropped price and currency columns stay in the table after the model sync.
	if not frappe.db.has_column("Sponsorship Tier", "price"):
		return

	tier = frappe.qb.DocType("Sponsorship Tier")
	tiers = frappe.qb.from_(tier).select(tier.name, tier.price, tier.currency).run(as_dict=True)
	for row in tiers:
		if frappe.db.exists("Buzz Price", {"parenttype": "Sponsorship Tier", "parent": row.name}):
			continue
		frappe.get_doc(
			{
				"doctype": "Buzz Price",
				"parenttype": "Sponsorship Tier",
				"parent": row.name,
				"parentfield": "prices",
				"idx": 1,
				"currency": row.currency or "INR",
				"price": row.price or 0,
			}
		).db_insert()
