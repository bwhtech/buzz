import frappe
from frappe.utils import get_file_json

MANIFEST = "public/islands/.vite/manifest.json"
ENTRY = "src/islands/main.ts"


def island_script() -> str | None:
	"""URL of the islands entry, which a Jinja page loads as a module script.

	None before `yarn build:islands` has run: an empty src would load the page itself.
	"""
	try:
		manifest = get_file_json(frappe.get_app_path("buzz", MANIFEST))
		return f"/assets/buzz/islands/{manifest[ENTRY]['file']}"
	except (FileNotFoundError, KeyError):
		return None
