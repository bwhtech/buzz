import frappe

# The themes used to render Event Category.icon_svg raw. That field is a Code field, which Frappe
# does not XSS-sanitize, so themes now draw a named icon instead. Backfill the bundled categories
# so an existing site keeps a meaningful icon instead of falling back to the generic one.
BUNDLED_CATEGORY_ICONS = {
	"Conferences": "users",
	"Local": "map-pin",
	"Meetups": "coffee",
	"Webinars": "monitor",
	"Yatra": "route",
	"Zoom Meeting": "video",
}


def execute():
	categories = frappe.get_all("Event Category", filters={"icon_name": ["in", ["", None]]}, fields=["name"])
	for category in categories:
		icon_name = BUNDLED_CATEGORY_ICONS.get(category.name)
		if icon_name:
			frappe.db.set_value("Event Category", category.name, "icon_name", icon_name)
