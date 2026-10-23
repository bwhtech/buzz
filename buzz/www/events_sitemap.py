import frappe

from buzz.playground import listing_filters
from buzz.www.event.meta import EventMeta

no_cache = 1
base_template_path = "www/sitemap.xml"


def get_context(context):
	filters = {"is_published": 1, "route": ["is", "set"]} | listing_filters()
	events = frappe.get_all("Buzz Event", filters=filters, fields=["route", "modified"])
	return {"links": [sitemap_link(event) for event in events]}


def sitemap_link(event) -> dict:
	return {"loc": EventMeta(event, {}).url(), "lastmod": f"{event.modified:%Y-%m-%d}"}
