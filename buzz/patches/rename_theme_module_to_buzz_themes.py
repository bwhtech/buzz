import frappe

OLD_MODULE = "Theme"
NEW_MODULE = "Buzz Themes"
THEME_DOCTYPES = ("Buzz Theme", "Buzz Theme Settings", "Buzz Themed Route")


def execute():
	"""Move the theme engine from module `Theme` to `Buzz Themes`.

	Runs pre-model-sync: DocType.module is a Link to Module Def, so the new
	module has to exist before the doctype JSONs (which already name it) sync,
	or every one of them fails to import."""
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

	# The Buzz Theme rows carry the module as data too — it is what resolves a
	# theme's backing app and therefore its folder on disk.
	if frappe.db.has_column("Buzz Theme", "module"):
		for theme_name in frappe.get_all("Buzz Theme", filters={"module": OLD_MODULE}, pluck="name"):
			frappe.db.set_value("Buzz Theme", theme_name, "module", NEW_MODULE, update_modified=False)

	frappe.delete_doc("Module Def", OLD_MODULE, ignore_permissions=True, force=True)
