import frappe

from buzz.api.themes import services
from buzz.api.themes.schemas import ThemeOptions


@frappe.whitelist()
def get_theme_options() -> ThemeOptions:
	return services.theme_options()
