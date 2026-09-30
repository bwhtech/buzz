import frappe

from buzz.utils import make_file_public


def execute():
	# An Event Sponsor copies its enquiry's logo URL, so one move serves both rows.
	moved = {}
	for doctype in ("Sponsorship Enquiry", "Event Sponsor"):
		rows = frappe.get_all(
			doctype, filters={"company_logo": ("like", "/private/%")}, fields=["name", "company_logo"]
		)
		for row in rows:
			if row.company_logo not in moved:
				moved[row.company_logo] = make_file_public(row.company_logo)
			frappe.db.set_value(
				doctype, row.name, "company_logo", moved[row.company_logo], update_modified=False
			)
