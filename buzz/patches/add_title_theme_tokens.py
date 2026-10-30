import frappe

from buzz.events.doctype.buzz_theme.buzz_theme import theme_css

TITLE_TOKENS = (
	{"token": "font-title", "type": "Font", "value": "League Gothic"},
	{"token": "title-size", "type": "Dimension", "value": "40px"},
)


def execute():
	"""Custom themes predate the title tokens; give them the title look pages always had."""
	for name in frappe.get_all("Buzz Theme", filters={"is_standard": 0}, pluck="name"):
		theme = frappe.get_doc("Buzz Theme", name)
		existing = {row.token for row in theme.tokens}
		for token in TITLE_TOKENS:
			if token["token"] not in existing:
				theme.append("tokens", token).db_insert()
	theme_css.clear_cache()
