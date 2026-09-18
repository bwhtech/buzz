import frappe
from frappe.utils.caching import redis_cache


@redis_cache(ttl=24 * 60 * 60)
def enabled_currencies() -> list[dict]:
	"""Currencies a System Manager has enabled on the site's Currency list."""
	return frappe.get_all(
		"Currency",
		filters={"enabled": 1},
		fields=["name", "symbol", "number_format"],
		order_by="name asc",
		ignore_permissions=True,
	)


def clear_currency_cache(doc, method=None):
	enabled_currencies.clear_cache()
