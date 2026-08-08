import os
import shutil

import frappe
from frappe.model.document import Document
from frappe.modules.utils import export_module_json


class BuzzTheme(Document):
	def validate(self):
		if self.parent_theme:
			self.validate_no_circular_inheritance()

	def after_insert(self):
		scaffold_theme(self.theme_name, self.module)

	@frappe.whitelist()
	def scaffold_theme_settings(self):
		settings_doctype_name = f"{self.theme_name} Settings"
		if frappe.db.exists("DocType", settings_doctype_name):
			frappe.throw(f"DocType '{settings_doctype_name}' already exists")

		create_theme_settings_doctype(settings_doctype_name, self.module)
		self.db_set("theme_settings", settings_doctype_name)
		return settings_doctype_name

	def after_rename(self, old_name, new_name, merge=False):
		old_slug = frappe.scrub(old_name)
		new_slug = frappe.scrub(new_name)

		if old_slug != new_slug:
			app_path = frappe.get_app_path(get_app_for_module(self.module))
			for base in (
				os.path.join(app_path, "themes"),
				os.path.join(app_path, "public", "themes"),
			):
				old_path = os.path.join(base, old_slug)
				new_path = os.path.join(base, new_slug)
				if os.path.isdir(old_path):
					os.rename(old_path, new_path)

			if self.module and frappe.conf.developer_mode:
				old_export_dir = get_theme_export_dir(self.module, old_slug)
				new_export_dir = get_theme_export_dir(self.module, new_slug)
				if os.path.isdir(old_export_dir):
					os.rename(old_export_dir, new_export_dir)
				# export_module_json names the json after the new slug, so the
				# old json lingers in the renamed folder unless we drop it.
				if os.path.isdir(new_export_dir):
					for filename in os.listdir(new_export_dir):
						if filename.endswith(".json") and filename != f"{new_slug}.json":
							os.remove(os.path.join(new_export_dir, filename))

		self.db_set("theme_name", new_name)

		if frappe.conf.developer_mode and self.is_standard and self.module:
			self.theme_name = new_name
			export_module_json(self, is_standard=True, module=self.module)

	def on_update(self):
		if not frappe.conf.developer_mode:
			return

		doc_before = self.get_doc_before_save()
		if doc_before:
			export_fields = [
				"theme_name",
				"parent_theme",
				"config",
				"is_standard",
				"module",
				"theme_settings",
			]
			if not any(self.get(field) != doc_before.get(field) for field in export_fields):
				return

		export_module_json(self, is_standard=bool(self.is_standard), module=self.module)

	def on_change(self):
		clear_theme_cache()

	def on_trash(self):
		paths = [get_theme_dir(self.name), get_theme_public_dir(self.name)]
		if self.module and frappe.conf.developer_mode:
			paths.append(get_theme_export_dir(self.module, frappe.scrub(self.name)))
		for path in paths:
			if os.path.isdir(path):
				shutil.rmtree(path)

	def validate_no_circular_inheritance(self):
		visited = {self.name}
		current = self.parent_theme
		while current:
			if current in visited:
				frappe.throw(f"Circular theme inheritance detected: {current}")
			visited.add(current)
			current = frappe.db.get_value("Buzz Theme", current, "parent_theme")


def create_theme_settings_doctype(doctype_name, module=None):
	is_developer_mode = bool(frappe.conf.get("developer_mode"))
	doctype = frappe.new_doc("DocType")
	doctype.update(
		{
			"name": doctype_name,
			"module": module or "Theme",
			"custom": 0 if is_developer_mode else 1,
			"issingle": 1,
			"naming_rule": "Expression (old style)",
			"autoname": f"{frappe.scrub(doctype_name)}",
			"fields": [
				{
					"fieldname": "info_section",
					"fieldtype": "Section Break",
					"label": "Theme Settings",
				},
			],
			"permissions": [
				{
					"role": "System Manager",
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
					"share": 1,
					"print": 1,
					"email": 1,
				},
				{
					"role": "Website Manager",
					"read": 1,
					"write": 1,
					"create": 1,
					"delete": 1,
					"share": 1,
					"print": 1,
					"email": 1,
				},
			],
		}
	)
	doctype.insert()
	return doctype


DEFAULT_THEME_APP = "buzz"


def get_app_for_module(module):
	"""App a Module Def belongs to; falls back to the engine app."""
	app = frappe.db.get_value("Module Def", module, "app_name") if module else None
	return app or DEFAULT_THEME_APP


def get_theme_app(theme_name):
	"""App whose files back a theme, resolved via its `module` field."""
	return get_app_for_module(frappe.db.get_value("Buzz Theme", theme_name, "module"))


def get_theme_dir(theme_name):
	"""Absolute path to a theme's folder: <app>/themes/<slug>."""
	return os.path.join(frappe.get_app_path(get_theme_app(theme_name)), "themes", frappe.scrub(theme_name))


def get_theme_public_dir(theme_name):
	"""Absolute path to a theme's static assets: <app>/public/themes/<slug>."""
	return os.path.join(
		frappe.get_app_path(get_theme_app(theme_name)), "public", "themes", frappe.scrub(theme_name)
	)


def get_theme_export_dir(module, slug):
	"""Absolute path to a theme's exported record folder under its module."""
	return os.path.join(frappe.get_module_path(module), "buzz_theme", slug)


def scaffold_theme(theme_name, module=None):
	app_path = frappe.get_app_path(get_app_for_module(module))
	slug = frappe.scrub(theme_name)
	theme_dir = os.path.join(app_path, "themes", slug)

	if os.path.exists(theme_dir):
		return

	for folder in (
		"pages",
		"components/includes",
		"components/macros",
	):
		os.makedirs(os.path.join(theme_dir, folder), exist_ok=True)

	for folder in ("css", "js", "images"):
		os.makedirs(os.path.join(app_path, "public", "themes", slug, folder), exist_ok=True)


def build_theme_context(theme_name):
	"""Resolved chain, folders, backing apps and settings DocType for one theme."""
	if not theme_name:
		return {"theme_name": None, "names": [], "dirs": [], "apps": {}, "settings_doctype": None}

	names = get_theme_names(theme_name)
	apps = {}
	dirs = []
	for name in names:
		app = get_theme_app(name)
		apps[name] = app
		theme_dir = os.path.join(frappe.get_app_path(app), "themes", frappe.scrub(name))
		if os.path.isdir(theme_dir):
			dirs.append(theme_dir)

	return {
		"theme_name": theme_name,
		"names": names,
		"dirs": dirs,
		"apps": apps,
		"settings_doctype": frappe.db.get_value("Buzz Theme", theme_name, "theme_settings"),
	}


PREVIEW_THEME_PARAM = "preview_theme"


def resolve_default_theme():
	"""Site-wide fallback theme. Buzz Settings is the single source of truth."""
	return frappe.get_single_value("Buzz Settings", "default_theme")


def resolve_theme_for_request(match):
	"""Theme for this request: previewed theme, else the matched event's own
	theme, else the site default.

	`match` is the regex match for the themed route, or None. A route that
	captures an `event_route` group is event-scoped, so the event it names
	chooses the theme; every other route (home, category, dynamic pages) has
	no event in scope and uses the site default."""
	preview_theme = requested_preview_theme()
	if preview_theme:
		return preview_theme

	event_route = (match.groupdict() or {}).get("event_route") if match else None
	if event_route:
		event_theme = frappe.db.get_value("Buzz Event", {"route": event_route}, "theme")
		if event_theme:
			return event_theme

	return resolve_default_theme()


def get_theme_context(theme_name):
	"""Resolved chain/dirs/apps for one theme, cached per theme name.

	Keyed per theme rather than as one global entry because several themes
	are now live on the same site at once — one per event."""
	if not theme_name:
		return build_theme_context(None)
	return frappe.cache.hget(
		"buzz_theme_context", theme_name, generator=lambda: build_theme_context(theme_name)
	)


def set_render_theme_context(context):
	"""Remember what the renderer resolved, so the Jinja helpers agree with it."""
	frappe.local.render_theme_context = context


def get_render_theme_context():
	"""Theme context for the current render.

	The renderer resolves the theme once (it needs the matched route to know
	which event is in scope) and stashes it here. buzz_theme_asset_url() and
	buzz_theme_config() must read that same context — if they re-resolved
	independently they would fall back to the site default and an event page
	would render its own theme's HTML with the default theme's assets."""
	context = getattr(frappe.local, "render_theme_context", None)
	if context is not None:
		return context
	return get_theme_context(resolve_theme_for_request(None))


def requested_preview_theme():
	"""Validated `?preview_theme=` value, or None."""
	if not frappe.conf.developer_mode:
		return None

	if not (hasattr(frappe.local, "request") and frappe.local.request):
		return None

	theme_name = frappe.local.request.args.get(PREVIEW_THEME_PARAM)
	if not theme_name:
		return None

	# An unknown name falls back to the route/site default rather than raising: a
	# mistyped query parameter should not take a page down.
	if not frappe.db.exists("Buzz Theme", theme_name):
		return None

	return theme_name


def get_theme_dirs(theme_name):
	"""Existing theme folders, child first, walking the inheritance chain."""
	dirs = []
	for name in get_theme_names(theme_name):
		theme_dir = get_theme_dir(name)
		if os.path.isdir(theme_dir):
			dirs.append(theme_dir)
	return dirs


def get_theme_names(theme_name):
	"""Theme names, child first, walking the parent_theme inheritance chain."""
	names = []
	visited = set()
	current = theme_name
	while current and current not in visited:
		visited.add(current)
		names.append(current)
		current = frappe.db.get_value("Buzz Theme", current, "parent_theme")
	return names


def clear_theme_cache():
	frappe.cache.delete_value("buzz_theme_context")
