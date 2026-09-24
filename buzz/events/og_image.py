import hashlib
import io
import math
from contextlib import contextmanager
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import format_date, getdate
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

from buzz.events.banner_pattern import rings_banner
from buzz.events.doctype.buzz_theme.buzz_theme import resolve_theme
from buzz.www.event.index import RANGE_SEPARATOR, EventPage, format_time

# Bump when the layout changes, so every event renders again on its next save
RENDER_VERSION = 1
WIDTH, HEIGHT, BANNER_HEIGHT = 1200, 630, 400
PADDING, COLUMN_GAP = 64, 48
FONTS = frappe.get_app_path("buzz", "public", "fonts")
WORDMARK = frappe.get_app_path("buzz", "public", "images", "buzz-wordmark-dark.png")
WORDMARK_SIZE = (54, 42)
COLOURS = {
	"light": {
		"page-bg": "#ffffff",
		"ink-title": "#111111",
		"ink-muted": "#6b6b6b",
		"border": "#ececec",
		"surface": "#f8f8f8",
	},
	"dark": {
		"page-bg": "#171717",
		"ink-title": "#f5f5f5",
		"ink-muted": "#a3a3a3",
		"border": "#2e2e2e",
		"surface": "#1f1f1f",
	},
}


def generate(event_name: str):
	# Not `event`: frappe.enqueue takes that keyword for itself
	doc = frappe.get_doc("Buzz Event", event_name)
	if not doc.is_published:
		return
	image = EventOgImage(doc)
	if not image.can_render():
		clear(doc)
	elif not image.is_current():
		image.save()


def enqueue_generate(event_name: str):
	frappe.enqueue(
		"buzz.events.og_image.generate",
		event_name=event_name,
		job_id=f"og-image-{event_name}",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def enqueue_all_published():
	for name in frappe.get_all(
		"Buzz Event", filters={"is_published": 1, "route": ["is", "set"]}, pluck="name"
	):
		enqueue_generate(str(name))


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
	return ImageFont.truetype(f"{FONTS}/Inter-{weight}.woff2", size)


def is_drawable(text: str) -> bool:
	# Inter covers Latin, Greek and Cyrillic; other scripts would draw as empty boxes.
	# A code-point range is coarser than reading the font's cmap, which needs fontTools.
	return all(ord(character) < 0x0530 or 0x1E00 <= ord(character) < 0x20D0 for character in text)


@contextmanager
def site_language():
	"""Render in the site's language so the hash is the same in a request and in the job."""
	previous = frappe.local.lang
	frappe.local.lang = frappe.db.get_default("lang") or "en"
	try:
		yield
	finally:
		frappe.local.lang = previous


class EventOgImage:
	def __init__(self, event):
		self.event = event
		self.colours = theme_colours(
			resolve_theme(event.theme, frappe.db.get_single_value("Buzz Settings", "event_page_theme"))
		)
		with site_language():
			self.meta_line = self.build_meta_line()

	def build_meta_line(self) -> str:
		page = EventPage(self.event.route)
		start, end = getdate(self.event.start_date), getdate(self.event.end_date or self.event.start_date)
		if start == end:
			time = format_time(self.event.start_time)
			date = " · ".join(
				part
				for part in [format_date(start, "EEE, d MMM"), time and f"{time} {page.timezone_label}"]
				if part
			)
		elif (start.year, start.month) == (end.year, end.month):
			date = f"{start.day}{RANGE_SEPARATOR}{format_date(end, 'd MMM')}"
		else:
			date = f"{format_date(start, 'd MMM')}{RANGE_SEPARATOR}{format_date(end, 'd MMM')}"
		venue = page.venue()
		place = _("Online") if self.event.medium == "Online" else venue and venue["name"]
		return " · ".join(part for part in [date, place] if part)

	def input_hash(self) -> str:
		parts = [
			RENDER_VERSION,
			self.event.title,
			self.meta_line,
			self.event.banner_image,
			self.colours,
			site_host(),
		]
		return hashlib.sha1(repr(parts).encode()).hexdigest()[:12]

	def file_name(self) -> str:
		return f"og-{self.input_hash()}.png"

	def is_current(self) -> bool:
		return bool(self.event.og_image and self.event.og_image.endswith(self.file_name()))

	def can_render(self) -> bool:
		return is_drawable(self.event.title + self.meta_line)

	def needs_update(self) -> bool:
		return not self.is_current() if self.can_render() else bool(self.event.og_image)

	def render(self) -> bytes:
		image = Image.new("RGB", (WIDTH, HEIGHT), self.colours["page-bg"])
		image.paste(self.banner(), (0, 0))
		draw = ImageDraw.Draw(image)
		draw.line([(0, BANNER_HEIGHT), (WIDTH, BANNER_HEIGHT)], fill=self.colours["border"], width=1)
		brand_width = self.draw_brand(image, draw)
		self.draw_text(draw, WIDTH - 2 * PADDING - brand_width - COLUMN_GAP)
		output = io.BytesIO()
		image.save(output, "PNG", optimize=True)
		return output.getvalue()

	def banner(self) -> Image.Image:
		uploaded = self.uploaded_banner()
		if not uploaded:
			return rings_banner(
				self.event.title, (WIDTH, BANNER_HEIGHT), self.colours["border"], self.colours["surface"]
			)
		# Transparent corners would turn black when flattened
		flat = Image.new("RGB", uploaded.size, self.colours["page-bg"])
		flat.paste(uploaded, mask=uploaded.convert("RGBA"))
		return ImageOps.fit(flat, (WIDTH, BANNER_HEIGHT), Image.LANCZOS)

	def uploaded_banner(self) -> Image.Image | None:
		url = self.event.banner_image
		if not url or urlparse(url).scheme:
			return None
		try:
			content = frappe.get_doc("File", {"file_url": url}).get_content()
			return Image.open(io.BytesIO(content))
		except Exception:
			return None

	def draw_text(self, draw: ImageDraw.ImageDraw, max_width: int):
		title_font, meta_font = font("SemiBold", 52), font("Medium", 26)
		top = BANNER_HEIGHT + (HEIGHT - BANNER_HEIGHT - (60 + 10 + 34)) // 2
		title = fit(self.event.title, title_font, max_width, tracking(52))
		draw_tracked(draw, (PADDING, top + 30), title, title_font, self.colours["ink-title"], tracking(52))
		meta = fit(self.meta_line, meta_font, max_width)
		draw.text(
			(PADDING, top + 60 + 10 + 17), meta, font=meta_font, fill=self.colours["ink-muted"], anchor="lm"
		)

	def draw_brand(self, image: Image.Image, draw: ImageDraw.ImageDraw) -> int:
		host_font, host = font("Medium", 20), site_host()
		top = BANNER_HEIGHT + (HEIGHT - BANNER_HEIGHT - (WORDMARK_SIZE[1] + 10 + 24)) // 2
		right = WIDTH - PADDING
		wordmark = recoloured_wordmark(self.colours["ink-title"])
		image.paste(wordmark, (right - WORDMARK_SIZE[0], top), wordmark)
		draw.text(
			(right, top + WORDMARK_SIZE[1] + 10 + 12),
			host,
			font=host_font,
			fill=self.colours["ink-muted"],
			anchor="rm",
		)
		return max(WORDMARK_SIZE[0], math.ceil(host_font.getlength(host)))

	def save(self):
		previous = attached_files(self.event.name)
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": self.file_name(),
				"attached_to_doctype": "Buzz Event",
				"attached_to_name": self.event.name,
				"attached_to_field": "og_image",
				"is_private": 0,
				"content": self.render(),
			}
		).insert(ignore_permissions=True)
		self.event.db_set("og_image", file.file_url, update_modified=False)
		delete_files(previous)


def attached_files(event_name: str) -> list[str]:
	return frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Buzz Event",
			"attached_to_name": event_name,
			"attached_to_field": "og_image",
		},
		pluck="name",
	)


def clear(event):
	event.db_set("og_image", None, update_modified=False)
	delete_files(attached_files(event.name))


def delete_files(names: list[str]):
	for name in names:
		frappe.delete_doc("File", name, ignore_permissions=True)


def theme_colours(theme: str | None) -> dict:
	scheme = frappe.db.get_value("Buzz Theme", theme, "color_scheme") if theme else "light"
	colours = dict(COLOURS.get(scheme, COLOURS["light"]))
	rows = frappe.get_all(
		"Buzz Theme Token",
		filters={"parenttype": "Buzz Theme", "parent": theme or "", "token": ["in", list(colours)]},
		fields=["token", "value", "dark_value"],
	)
	for row in rows:
		value = row.dark_value if scheme == "dark" and row.dark_value else row.value
		try:
			colours[row.token] = "#%02x%02x%02x" % ImageColor.getrgb(value)[:3]
		except ValueError:
			pass  # oklch() and other CSS-only syntax keep the scheme default
	return colours


def site_host() -> str:
	# Not get_url(): in a request it follows the Host header, which the job never sees
	host = frappe.local.conf.host_name or frappe.local.conf.hostname or frappe.local.site
	return urlparse(host if "://" in host else f"//{host}").hostname or ""


def tracking(size: int) -> float:
	return -0.03 * size


def text_width(text: str, typeface: ImageFont.FreeTypeFont, letter_spacing: float = 0) -> float:
	return typeface.getlength(text) + letter_spacing * max(len(text) - 1, 0)


def fit(text: str, typeface: ImageFont.FreeTypeFont, max_width: float, letter_spacing: float = 0) -> str:
	if text_width(text, typeface, letter_spacing) <= max_width:
		return text
	while text and text_width(text + "…", typeface, letter_spacing) > max_width:
		text = text[:-1]
	return text.rstrip() + "…"


def draw_tracked(draw, position, text, typeface, fill, letter_spacing):
	# Pillow has no letter-spacing; placing each glyph at the kerned prefix width keeps kerning
	x, y = position
	for index, character in enumerate(text):
		offset = typeface.getlength(text[:index]) + letter_spacing * index
		draw.text((x + offset, y), character, font=typeface, fill=fill, anchor="lm")


def recoloured_wordmark(colour: str) -> Image.Image:
	source = Image.open(WORDMARK).convert("RGBA").resize(WORDMARK_SIZE, Image.LANCZOS)
	wordmark = Image.new("RGBA", WORDMARK_SIZE, colour)
	wordmark.putalpha(source.getchannel("A"))
	return wordmark
