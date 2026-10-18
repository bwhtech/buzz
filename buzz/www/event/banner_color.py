import os

import frappe
from frappe.utils.caching import redis_cache
from PIL import Image


def banner_color(file_url: str | None) -> str | None:
	"""The banner's average colour, painted behind it while the image loads."""
	if not file_url or not file_url.startswith("/files/") or ".." in file_url:
		return None
	path = frappe.get_site_path("public", file_url.lstrip("/"))
	try:
		return average_color(path, os.path.getmtime(path))
	except OSError:
		return None


# The modified time is part of the cache key, so a replaced file gets a fresh colour.
@redis_cache(ttl=None)
def average_color(path: str, modified: float) -> str | None:
	try:
		with Image.open(path) as image:
			red, green, blue = image.convert("RGB").resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
	except (OSError, Image.DecompressionBombError):
		return None
	return f"#{red:02x}{green:02x}{blue:02x}"
