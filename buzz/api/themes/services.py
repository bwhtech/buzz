import frappe
from frappe.utils import today

from buzz.api.themes.schemas import ThemeOptions
from buzz.events.doctype.buzz_theme.tokens import FONT_STACKS


def theme_options() -> ThemeOptions:
	return ThemeOptions(
		can_edit=bool(frappe.has_permission("Buzz Theme", "write")),
		fonts=FONT_STACKS,
		preview_route=preview_route(),
	)


def preview_route() -> str | None:
	"""The soonest upcoming published event, to preview themes on."""
	routes = frappe.get_all(
		"Buzz Event",
		filters={"is_published": 1, "route": ["is", "set"], "end_date": [">=", today()]},
		pluck="route",
		order_by="start_date asc",
		limit=1,
	)
	return routes[0] if routes else None
