import frappe

THEME_HEX = {
	"gray": "#7c7c7c",
	"blue": "#3b82f6",
	"green": "#22a06b",
	"red": "#ef4444",
	"orange": "#f97316",
	"yellow": "#eab308",
	"teal": "#14b8a6",
	"cyan": "#06b6d4",
	"purple": "#8b5cf6",
	"pink": "#ec4899",
}


def execute():
	"""Item type colors are now a Color field, so swap theme names for their hex values."""
	for name, hex_color in THEME_HEX.items():
		frappe.db.set_value(
			"Buzz Schedule Item Type", {"color": name}, "color", hex_color, update_modified=False
		)
