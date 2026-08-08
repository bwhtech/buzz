import json
import os
import shutil

import frappe
from frappe.model.document import Document
from frappe.modules.utils import export_module_json


class BuzzTheme(Document):
	def validate(self):
		if self.parent_theme:
			self.validate_no_circular_inheritance()
		if self.is_active:
			self.deactivate_other_themes()

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

	def before_export(self, doc_export):
		doc_export["is_active"] = 0

	def on_change(self):
		clear_active_theme_cache()
		# Write the manifest only once the row is durable: an in-transaction
		# rollback after on_change would otherwise leave active_theme.json (read
		# by the Vite plugin) pointing at a theme the DB no longer reflects.
		frappe.db.after_commit.add(save_active_theme_manifest)

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

	def deactivate_other_themes(self):
		other_active_themes = frappe.get_all(
			"Buzz Theme",
			filters={"is_active": 1, "name": ("!=", self.name)},
			pluck="name",
		)
		for theme_name in other_active_themes:
			frappe.db.set_value("Buzz Theme", theme_name, "is_active", 0)


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


def get_active_theme():
	return frappe.cache.get_value("buzz_active_theme", generator=resolve_active_theme)


def resolve_active_theme():
	return frappe.db.get_value("Buzz Theme", {"is_active": 1}, "theme_name")


def get_active_theme_context():
	"""Resolved inheritance chain for the active theme, cached as one entry.

	Carries the chain names (child first), the theme folders that exist on
	disk, the backing app per theme, and the linked settings DocType. This
	replaces the uncached DB walks that `can_render` ran on every request and
	that `theme_asset_url` / `theme_config` ran per call. Invalidated on any
	theme change via `clear_active_theme_cache`."""
	return frappe.cache.get_value("buzz_active_theme_context", generator=build_active_theme_context)


def build_active_theme_context():
	return build_theme_context(resolve_active_theme())


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


def get_render_theme_context():
	"""Theme context for the current render: the active theme, or a previewed one.

	A site has exactly one active theme, which makes developing a second theme
	awkward — you cannot look at it without switching the live site over. A
	`?preview_theme=<name>` parameter resolves that theme's chain for this
	request only, so several themes can be built and screenshotted side by side.

	Gated on `developer_mode`: letting a request choose which templates render is
	fine on a developer's machine and is not something a production site should
	expose."""
	preview_theme = requested_preview_theme()
	if not preview_theme:
		return get_active_theme_context()

	# Per-request memo — `can_render`, `theme_asset_url` and `theme_config` each
	# ask for this, and rebuilding walks the inheritance chain every time.
	cached = getattr(frappe.local, "preview_theme_context", None)
	if cached and cached["theme_name"] == preview_theme:
		return cached

	context = build_theme_context(preview_theme)
	frappe.local.preview_theme_context = context
	return context


def requested_preview_theme():
	"""Validated `?preview_theme=` value, or None."""
	if not frappe.conf.developer_mode:
		return None

	if not (hasattr(frappe.local, "request") and frappe.local.request):
		return None

	theme_name = frappe.local.request.args.get(PREVIEW_THEME_PARAM)
	if not theme_name:
		return None

	# An unknown name falls back to the active theme rather than raising: a
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


def clear_active_theme_cache():
	frappe.cache.delete_value("buzz_active_theme")
	frappe.cache.delete_value("buzz_active_theme_context")


def save_active_theme_manifest():
	"""Write `active_theme.json` at the buzz app root, read by the Vite
	plugin at build time. Carries absolute per-theme folder paths so the plugin
	stays app-agnostic when themes live across different content apps."""
	engine_module_path = frappe.get_app_path(DEFAULT_THEME_APP)
	app_root = os.path.dirname(engine_module_path)
	manifest_path = os.path.join(app_root, "active_theme.json")

	theme_name = resolve_active_theme()
	names = get_theme_names(theme_name) if theme_name else []
	theme_dirs = [get_theme_dir(name) for name in names]

	manifest = {
		"active_theme": theme_name,
		# Slugs, not names: a display name like "Buzz Events Theme" is scrubbed
		# to its folder name.
		"theme_chain": [frappe.scrub(name) for name in names],
		"theme_dirs": theme_dirs,
		"themes_dir": os.path.dirname(theme_dirs[0])
		if theme_dirs
		else os.path.join(engine_module_path, "themes"),
	}
	with open(manifest_path, "w") as manifest_file:
		json.dump(manifest, manifest_file, indent=2)
