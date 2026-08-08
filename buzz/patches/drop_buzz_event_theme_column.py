import frappe


def execute():
	if not frappe.db.has_column("Buzz Event", "theme"):
		return

	frappe.db.sql_ddl("ALTER TABLE `tabBuzz Event` DROP COLUMN `theme`")

	frappe.client_cache.delete_value("table_columns::tabBuzz Event")
