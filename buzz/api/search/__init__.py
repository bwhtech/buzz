import frappe

from buzz.api.search import services
from buzz.api.search.schemas import EventSearchResponse, PaletteEventsResponse


@frappe.whitelist()
def get_palette_events() -> PaletteEventsResponse:
	return services.palette_events(frappe.session.user)


@frappe.whitelist()
def search_event(event: str, term: str, section: str | None = None) -> EventSearchResponse:
	return services.EventSearch(event, section).run(term)
