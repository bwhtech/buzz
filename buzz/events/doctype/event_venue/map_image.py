import hashlib
import io
import re
from functools import cache

import frappe
from PIL import Image, ImageDraw

from buzz.events.doctype.event_venue.details import VenueLocation
from buzz.events.og_text import font
from buzz.www.event.dot_map import COARSE_DOTS, FINE_DOTS, DotMap

# Bump when the drawing changes, so every venue renders again on its next email
RENDER_VERSION = 1
# Twice the email's 536px column, for sharp pins on high density screens
WIDTH, HEIGHT = 1072, 670
COLOURS = {"background": "#f6f6f6", "land": "#c8c8c8", "pin": "#171717", "number": "#ffffff"}
PIN_RADIUS, PIN_RING = 36, 12
DOT_FILES = {FINE_DOTS["url"]: "world-dots.svg", COARSE_DOTS["url"]: "world-dots-coarse.svg"}


class LocationsMapImage:
	"""A grouped venue's locations as numbered pins on the event page's dot map, for emails,
	which cannot run the interactive map."""

	def __init__(self, venue: str, locations: list[VenueLocation]):
		self.venue = venue
		self.pins = {
			number: (location.latitude, location.longitude)
			for number, location in enumerate(locations, 1)
			if location.latitude and location.longitude
		}

	def url(self) -> str | None:
		if not self.pins:
			return None
		return self.saved_url() or self.save()

	def file_name(self) -> str:
		parts = repr([RENDER_VERSION, sorted(self.pins.items())])
		return f"locations-map-{hashlib.sha1(parts.encode()).hexdigest()[:12]}.png"

	def saved_url(self) -> str | None:
		filters = {
			"file_name": self.file_name(),
			"attached_to_doctype": "Event Venue",
			"attached_to_name": self.venue,
		}
		return frappe.db.get_value("File", filters, "file_url")

	def save(self) -> str:
		return (
			frappe.get_doc(
				{
					"doctype": "File",
					"file_name": self.file_name(),
					"attached_to_doctype": "Event Venue",
					"attached_to_name": self.venue,
					"is_private": 0,
					"content": self.render(),
				}
			)
			.insert(ignore_permissions=True)
			.file_url
		)

	def render(self) -> bytes:
		dot_map = DotMap(list(self.pins.values()))
		image = Image.new("RGB", (WIDTH, HEIGHT), COLOURS["background"])
		draw = ImageDraw.Draw(image)
		self.draw_land(draw, dot_map)
		for number, (latitude, longitude) in self.pins.items():
			pin = dot_map.pin(latitude, longitude)
			self.draw_pin(draw, number, pin["x"] / 100 * WIDTH, pin["y"] / 100 * HEIGHT)
		output = io.BytesIO()
		image.save(output, "PNG", optimize=True)
		return output.getvalue()

	def draw_land(self, draw: ImageDraw.ImageDraw, dot_map: DotMap):
		view, scale = dot_map.view, WIDTH / dot_map.view.width
		radius = dot_map.dot_width / 2 * scale
		for x, y in land_dots(dot_map.dots_url):
			left, top = (x - view.x) * scale, (y - view.y) * scale
			if -radius <= left <= WIDTH + radius and -radius <= top <= HEIGHT + radius:
				draw.ellipse((left - radius, top - radius, left + radius, top + radius), fill=COLOURS["land"])

	def draw_pin(self, draw: ImageDraw.ImageDraw, number: int, x: float, y: float):
		ring = PIN_RADIUS + PIN_RING
		draw.ellipse((x - ring, y - ring, x + ring, y + ring), fill=COLOURS["background"])
		draw.ellipse((x - PIN_RADIUS, y - PIN_RADIUS, x + PIN_RADIUS, y + PIN_RADIUS), fill=COLOURS["pin"])
		draw.text((x, y), str(number), font=font("SemiBold", 36), fill=COLOURS["number"], anchor="mm")


@cache
def land_dots(dots_url: str) -> list[tuple[float, float]]:
	"""The dots of the dot map's SVG, each drawn as a zero length path segment."""
	svg = frappe.read_file(frappe.get_app_path("buzz", "public", "images", DOT_FILES[dots_url]))
	return [(float(x), float(y)) for x, y in re.findall(r"M([\d.]+) ([\d.]+)h0", svg)]
