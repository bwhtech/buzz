import frappe


def execute():
	"""Drop the column left behind when Buzz Event.theme was removed.

	Themes are a single site-wide setting now, but removing a field only drops
	its DocField - the column and its stale values survive every migrate. DDL
	has no query-builder equivalent, so this mirrors how frappe/erpnext write
	their own drop patches: guard on has_column, then sql_ddl."""
	if not frappe.db.has_column("Buzz Event", "theme"):
		return

	frappe.db.sql_ddl("ALTER TABLE `tabBuzz Event` DROP COLUMN `theme`")

	# has_column() answers from a cached column list that the DDL above does not
	# touch, so without this every already-running worker keeps building SQL for
	# a column the table no longer has. Same key frappe's own schema code drops.
	frappe.client_cache.delete_value("table_columns::tabBuzz Event")
