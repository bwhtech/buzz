import json

import frappe

MANIFEST = "public/islands/.vite/manifest.json"
ENTRY = "src/islands/main.ts"


def island_script() -> str | None:
	"""URL of the islands entry, which a Jinja page loads as a module script.

	None before `yarn build:islands` has run: an empty src would load the page itself.
	"""
	path = frappe.get_app_path("buzz", MANIFEST)
	try:
		with open(path) as manifest:
			return f"/assets/buzz/islands/{json.load(manifest)[ENTRY]['file']}"
	except (FileNotFoundError, KeyError):
		return None
