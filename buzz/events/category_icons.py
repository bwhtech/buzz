SVG_OPEN = (
	'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40" fill="none" '
	'stroke="#8C8C8C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
)


def draw(shapes: str) -> str:
	return f"{SVG_OPEN}{shapes}</svg>"


# Seeded on install; buzz.patches.update_seeded_category_icons refreshes unedited ones.
CATEGORY_ICONS = {
	"Meetups": draw(
		'<circle cx="13" cy="15" r="4"/><circle cx="27" cy="15" r="4"/>'
		'<path d="M6 31c0-4.4 3.1-8 7-8s7 3.6 7 8"/><path d="M20 31c0-4.4 3.1-8 7-8s7 3.6 7 8"/>'
	),
	"Conferences": draw(
		'<path d="M4 33h32"/><path d="M15 33V22h10v11"/><path d="M13 22h14"/>'
		'<path d="M20 22v-4"/><circle cx="20" cy="15" r="2.5"/><path d="M8 7l4 4M32 7l-4 4"/>'
	),
	"Local": draw(
		'<path d="M20 35s-10-9.5-10-17a10 10 0 0 1 20 0c0 7.5-10 17-10 17z"/><circle cx="20" cy="18" r="3.5"/>'
	),
	"Webinars": draw(
		'<rect x="5" y="8" width="30" height="20" rx="3"/><path d="M15 33h10M20 28v5"/>'
		'<path d="M17.5 14.5v7l6-3.5z"/>'
	),
	"Zoom Meeting": draw(
		'<rect x="4" y="12" width="22" height="16" rx="3"/><path d="M26 18l10-5v14l-10-5"/>'
	),
}
