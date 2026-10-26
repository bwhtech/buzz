import frappe


def execute():
	"""The Buzz Event Form doctype is gone; its emptied table is left behind."""
	if frappe.db.table_exists("Buzz Event Form") and not frappe.db.count("Buzz Event Form"):
		frappe.db.sql_ddl("drop table `tabBuzz Event Form`")
