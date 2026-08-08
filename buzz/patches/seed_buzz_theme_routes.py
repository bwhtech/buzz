import frappe

ROUTES = [
	{"url_pattern": "^$", "template_path": "pages/home.html", "requires_auth": 0},
	{"url_pattern": "^home$", "template_path": "pages/home.html", "requires_auth": 0},
	{"url_pattern": "^events$", "template_path": "pages/events.html", "requires_auth": 0},
	{
		"url_pattern": "^events/(?P<event_route>[^/]+)$",
		"template_path": "pages/events/detail.html",
		"requires_auth": 0,
	},
	{
		"url_pattern": "^category/(?P<category_slug>[^/]+)$",
		"template_path": "pages/category/detail.html",
		"requires_auth": 0,
	},
]


def execute():
	# Route table used to live only in one dev site's database; ship it with the app so
	# every site gets the default routes. Idempotent: only appends rows an operator
	# hasn't already added by hand, matched on url_pattern.
	settings = frappe.get_single("Buzz Theme Settings")
	existing_patterns = {row.url_pattern for row in settings.routes}

	changed = False
	for route in ROUTES:
		if route["url_pattern"] in existing_patterns:
			continue
		settings.append("routes", route)
		changed = True

	if changed:
		settings.save(ignore_permissions=True)
