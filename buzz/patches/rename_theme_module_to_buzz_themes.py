import frappe

OLD_MODULE = "Theme"
NEW_MODULE = "Buzz Themes"
THEME_DOCTYPES = ("Buzz Theme", "Buzz Theme Settings", "Buzz Themed Route")


def execute():
	if not frappe.db.exists("Module Def", OLD_MODULE):
		return

	if not frappe.db.exists("Module Def", NEW_MODULE):
		module_def = frappe.new_doc("Module Def")
		module_def.module_name = NEW_MODULE
		module_def.app_name = "buzz"
		module_def.insert(ignore_permissions=True)

	for doctype in THEME_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			frappe.db.set_value("DocType", doctype, "module", NEW_MODULE, update_modified=False)

	if frappe.db.has_column("Buzz Theme", "module"):
		for theme_name in frappe.get_all("Buzz Theme", filters={"module": OLD_MODULE}, pluck="name"):
			frappe.db.set_value("Buzz Theme", theme_name, "module", NEW_MODULE, update_modified=False)

	frappe.delete_doc("Module Def", OLD_MODULE, ignore_permissions=True, force=True)
