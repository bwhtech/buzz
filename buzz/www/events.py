import frappe
from frappe import _
from frappe.utils import get_url, today

from buzz.www.event.index import format_day, not_found
from buzz.www.site_header import apply_site_context

no_cache = 1
LISTING_LIMIT = 60


def get_context(context):
	apply_site_context(context)
	context.update(EventListing(frappe.form_dict.category).as_context())


class EventListing:
	def __init__(self, category_slug: str | None = None):
		self.category = self.load_category(category_slug) if category_slug else None

	def load_category(self, slug: str) -> frappe._dict:
		category = frappe.db.get_value(
			"Event Category",
			{"slug": slug, "enabled": 1},
			["name", "slug", "description", "banner_image"],
			as_dict=True,
		)
		return category or not_found()

	def as_context(self) -> dict:
		title = self.category.name if self.category else _("Upcoming events")
		return {
			"title": title,
			"category": self.category,
			"categories": self.categories(),
			"events": [self.card(event) for event in self.events()],
			"meta": {
				"url": get_url("/events"),
				"description": self.category.description if self.category else "",
			},
		}

	def categories(self) -> list:
		return frappe.get_all(
			"Event Category",
			filters={"enabled": 1, "slug": ["is", "set"]},
			fields=["name", "slug"],
			order_by="name",
		)

	def events(self) -> list:
		filters = {"is_published": 1, "route": ["is", "set"], "end_date": [">=", today()]}
		if self.category:
			filters["category"] = self.category.name
		return frappe.get_all(
			"Buzz Event",
			filters=filters,
			fields=["title", "route", "start_date", "medium", "venue", "card_image", "banner_image"],
			order_by="start_date asc",
			limit=LISTING_LIMIT,
		)

	def card(self, event) -> dict:
		return {
			"title": event.title,
			"url": f"/events/{event.route}",
			"date": format_day(event.start_date),
			"place": _("Online") if event.medium == "Online" else event.venue,
			"image": event.card_image or event.banner_image,
		}
