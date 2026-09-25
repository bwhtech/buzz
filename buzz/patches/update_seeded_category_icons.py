import frappe

from buzz.events.category_icons import CATEGORY_ICONS


def execute():
	for name, icon_svg in CATEGORY_ICONS.items():
		category = frappe.db.get_value("Event Category", name, ["creation", "modified"], as_dict=True)
		# Never edited since install: replacing the icon loses nothing an admin chose.
		if category and category.creation == category.modified:
			frappe.db.set_value("Event Category", name, "icon_svg", icon_svg, update_modified=False)
