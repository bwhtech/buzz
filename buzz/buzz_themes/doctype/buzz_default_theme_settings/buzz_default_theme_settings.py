import frappe
from frappe.model.document import Document

# Canonical dashboard routes: /dashboard/* is redirected to /b/* by website_redirects in hooks.py,
# so link at /b directly and skip the hop. Proposals live at /event-proposal (see dashboard/src/router.ts).
DEFAULT_NAV_LINKS = [
	{"label": "Dashboard", "url": "/b", "open_in_new_tab": 0},
	{"label": "Propose Event", "url": "/b/event-proposal", "open_in_new_tab": 0},
]


class BuzzDefaultThemeSettings(Document):
	def get_nav_links(self):
		"""Header links, falling back to the bundled defaults while the table is empty."""
		if self.nav_links:
			return self.nav_links

		return [frappe._dict(link) for link in DEFAULT_NAV_LINKS]
