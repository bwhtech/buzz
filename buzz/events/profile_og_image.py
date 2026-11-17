"""The share image of /@<username>: the owner's name under a spotlight of the Buzz rings."""

from urllib.parse import urlparse

import frappe
from frappe import _
from PIL import Image, ImageDraw, ImageOps

from buzz.events.banner_pattern import rings_banner
from buzz.events.doctype.buzz_team.buzz_team import (
	personal_team_of,
	personal_team_owner,
	personal_teams_enabled,
)
from buzz.events.doctype.buzz_team.team_page import TeamPage
from buzz.events.og_image import (
	COLOURS,
	HEIGHT,
	PADDING,
	WIDTH,
	OgImage,
	clear,
	png_bytes,
	recoloured_wordmark,
	render_if_stale,
	site_language,
	uploaded_image,
)
from buzz.events.og_text import OgText, font, is_drawable, tracking, wrap_lines

RENDER_VERSION = 1

CONTENT_WIDTH = WIDTH - 2 * PADDING
SPOTLIGHT_CENTRE = (936, 0)
RINGS_RADII, GLOW_RADII, GLOW_ALPHA = (960, 600), (720, 420), 36
AVATAR_SIZE, AVATAR_GAP, HANDLE_SIZE = 56, 16, 26
NAME_SIZE, NAME_LINES, NAME_LINE_HEIGHT = 80, 2, 86
BIO_SIZE, BIO_LINE_HEIGHT, BLOCK_GAP = 28, 40, 20
SCALE = 2  # the avatar is drawn at 2x and scaled down, so its edge is smooth
USER_FIELDS = ("full_name", "user_image", "bio", "username")


def generate(team_name: str):
	if not frappe.db.exists("Buzz Team", team_name):
		return
	team = frappe.get_doc("Buzz Team", team_name)
	owner = profile_owner(team)
	if not owner:
		clear(team)
		return
	image = ProfileOgImage(team, owner)
	# A photo that fails to load keeps the current image, so the next run retries
	if not image.avatar_failed_to_load():
		render_if_stale(image)


def profile_owner(team) -> frappe._dict | None:
	"""The owner whose profile shows this team, while that profile is public."""
	if not (team.is_personal and personal_teams_enabled()):
		return None
	if not frappe.db.exists("Buzz Event", {"team": team.name, "is_published": 1}):
		return None
	owner = personal_team_owner(team.name)
	return owner if owner and owner.username else None


def enqueue_generate(team_name: str):
	frappe.enqueue(
		"buzz.events.profile_og_image.generate",
		team_name=team_name,
		job_id=f"og-image-profile-{team_name}",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def enqueue_for_user(doc, event=None):
	"""User on_update: the name, photo, bio and username are drawn on the profile's image."""
	if frappe.in_test or not any(doc.has_value_changed(field) for field in USER_FIELDS):
		return
	if team := personal_team_of(doc.name):
		enqueue_generate(team)


class ProfileOgImage(OgImage):
	"""Dark, after Linear's share cards: rings and a soft light fall from the top right."""

	render_version = RENDER_VERSION

	def __init__(self, team, owner: frappe._dict):
		self.team, self.doc = team, team
		self.owner = owner
		self.name = owner.full_name or owner.username
		self.colours = dict(COLOURS["dark"])
		self.avatar = uploaded_image(owner.user_image)
		with site_language():
			self.subtitle = self.build_subtitle()

	def build_subtitle(self) -> str:
		count = TeamPage(self.team).hosted_count
		hosted = _("1 event hosted") if count == 1 else _("{0} events hosted").format(count)
		return f"@{self.owner.username} · {hosted}"

	def bio(self) -> str:
		text = " ".join((self.owner.bio or "").split())
		return text if is_drawable(text) else ""

	def hash_parts(self) -> list:
		return [self.name, self.subtitle, self.bio(), self.owner.user_image]

	def can_render(self) -> bool:
		return is_drawable(self.name + self.subtitle)

	def avatar_failed_to_load(self) -> bool:
		"""A stored photo that cannot be read. An external URL is deliberately drawn as a monogram."""
		photo = self.owner.user_image
		return bool(photo) and not urlparse(photo).scheme and self.avatar is None

	def render(self) -> bytes:
		image = Image.new("RGB", (WIDTH, HEIGHT), self.colours["page-bg"])
		self.draw_spotlight(image)
		wordmark = recoloured_wordmark(self.colours["ink-title"])
		image.paste(wordmark, (PADDING, PADDING), wordmark)
		name_top = self.draw_name(image, self.draw_bio(image, HEIGHT - PADDING))
		self.draw_identity(image, name_top - BLOCK_GAP - AVATAR_SIZE // 2)
		return png_bytes(image)

	def draw_spotlight(self, image: Image.Image):
		rings = rings_banner(
			self.owner.username, (WIDTH, HEIGHT), self.colours["border"], self.colours["page-bg"]
		)
		image.paste(rings, (0, 0), radial_mask(RINGS_RADII, 255))
		image.paste(Image.new("RGB", image.size, "#ffffff"), (0, 0), radial_mask(GLOW_RADII, GLOW_ALPHA))

	def draw_bio(self, image: Image.Image, bottom: int) -> int:
		"""One line of bio above `bottom`; returns where the block above it ends."""
		bio = self.bio()
		if not bio:
			return bottom
		line = OgText(bio, font("Medium", BIO_SIZE)).fit(CONTENT_WIDTH)
		line.draw(image, (PADDING, bottom - BIO_LINE_HEIGHT // 2), self.colours["ink-muted"])
		return bottom - BIO_LINE_HEIGHT - BLOCK_GAP

	def draw_name(self, image: Image.Image, bottom: int) -> int:
		typeface = font("SemiBold", NAME_SIZE)
		lines = wrap_lines(self.name, typeface, CONTENT_WIDTH, NAME_LINES)
		top = bottom - len(lines) * NAME_LINE_HEIGHT
		for index, line in enumerate(lines):
			middle = top + index * NAME_LINE_HEIGHT + NAME_LINE_HEIGHT // 2
			OgText(line, typeface, tracking(NAME_SIZE)).draw(
				image, (PADDING, middle), self.colours["ink-title"]
			)
		return top

	def draw_identity(self, image: Image.Image, middle: int):
		avatar = self.avatar_image()
		image.paste(avatar, (PADDING, middle - AVATAR_SIZE // 2), avatar)
		subtitle = OgText(self.subtitle, font("Medium", HANDLE_SIZE))
		left = PADDING + AVATAR_SIZE + AVATAR_GAP
		subtitle.fit(WIDTH - PADDING - left).draw(image, (left, middle), self.colours["ink-muted"])

	def avatar_image(self) -> Image.Image:
		side = AVATAR_SIZE * SCALE
		picture = self.photo(side) if self.avatar else self.monogram(side)
		mask = Image.new("L", (side, side), 0)
		ImageDraw.Draw(mask).ellipse((0, 0, side - 1, side - 1), fill=255)
		picture.putalpha(mask)
		return picture.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)

	def photo(self, side: int) -> Image.Image:
		# Transparent corners would turn black when flattened
		photo = self.avatar.convert("RGBA")
		flat = Image.new("RGB", photo.size, self.colours["page-bg"])
		flat.paste(photo, mask=photo)
		return ImageOps.fit(flat, (side, side), Image.LANCZOS)

	def monogram(self, side: int) -> Image.Image:
		mark = Image.new("RGB", (side, side), self.colours["border"])
		letter = self.name[:1].upper() or "?"
		typeface = font("SemiBold", round(side * 0.43))
		ImageDraw.Draw(mark).text(
			(side / 2, side / 2), letter, font=typeface, fill=self.colours["ink-title"], anchor="mm"
		)
		return mark


def radial_mask(radii: tuple[int, int], peak: int) -> Image.Image:
	"""`peak` at SPOTLIGHT_CENTRE, easing to clear at `radii` from it."""
	gradient = Image.radial_gradient("L")
	# The gradient reaches 255 only in its corners; this is its value on the inscribed circle
	edge = gradient.getpixel((0, gradient.height // 2))
	falloff = gradient.point(lambda value: round(peak * max(0, 1 - value / edge) ** 2))
	falloff = falloff.resize((2 * radii[0], 2 * radii[1]), Image.BILINEAR)
	mask = Image.new("L", (WIDTH, HEIGHT), 0)
	mask.paste(falloff, (SPOTLIGHT_CENTRE[0] - radii[0], SPOTLIGHT_CENTRE[1] - radii[1]))
	return mask
