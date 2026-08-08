import os
import re
import shutil

import frappe
from frappe.model.document import Document
from frappe.modules.utils import export_module_json

# A theme name reaches the filesystem as `frappe.scrub(name)`, which keeps path
# separators ("../../evil name" -> "../../evil_name"), and frappe's own name
# validation only rejects `<` and `>`. Constrain the name at the source.
THEME_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")


class BuzzTheme(Document):
	def validate(self):
		validate_theme_name(self.theme_name)
		if self.parent_theme:
			self.validate_no_circular_inheritance()

	def after_insert(self):
		# Scaffolding writes into the app directory, which is read-only on a
		# production deployment.
		if frappe.conf.developer_mode:
			scaffold_theme(self.theme_name, self.module)

	@frappe.whitelist(methods=["POST"])
	def scaffold_theme_settings(self):
		# `run_doc_method` only enforces READ, so a whitelisted method that
		# creates a DocType has to check for itself.
		self.check_permission("write")

		settings_doctype_name = f"{self.theme_name} Settings"
		if frappe.db.exists("DocType", settings_doctype_name):
			frappe.throw(f"DocType '{settings_doctype_name}' already exists")

		create_theme_settings_doctype(settings_doctype_name, self.module)
		self.db_set("theme_settings", settings_doctype_name)
		return settings_doctype_name

	def after_rename(self, old_name, new_name, merge=False):
		# `rename_doc` does not re-run `validate`, so the new name arrives here
		# unchecked.
		validate_theme_name(new_name)
		validate_theme_name(old_name)

		old_slug = frappe.scrub(old_name)
		new_slug = frappe.scrub(new_name)

		if old_slug != new_slug:
			app_path = frappe.get_app_path(get_app_for_module(self.module))
			for base in (
				os.path.join(app_path, "themes"),
				os.path.join(app_path, "public", "themes"),
			):
				old_path = get_contained_path(base, old_slug)
				new_path = get_contained_path(base, new_slug)
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
		# A standard theme's folders are shipped app source, not site data —
		# deleting the record from Desk must never wipe them off disk. Only a
		# developer-mode site owns the folders it scaffolded itself.
		if not frappe.conf.developer_mode or self.is_standard:
			return

		validate_theme_name(self.name)
		paths = [get_theme_dir(self.name), get_theme_public_dir(self.name)]
		if self.module:
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


def validate_theme_name(theme_name):
	if not THEME_NAME_PATTERN.match(theme_name or ""):
		frappe.throw(
			frappe._("Theme name may only contain letters, numbers, spaces, hyphens and underscores")
		)


def is_within_directory(directory, target):
	"""True if `target` resolves to a path inside `directory`.

	Guards every lookup that folds a request path, a theme name or a
	template-supplied include path into a filesystem path: a `..` segment that
	survives upstream normalization must not let a render escape the theme
	folder (file disclosure / SSTI surface), nor let a delete escape it. Don't
	trust werkzeug — or `frappe.scrub` — to have normalized it."""
	directory = os.path.realpath(directory)
	target = os.path.realpath(target)
	return target == directory or target.startswith(directory + os.sep)


def get_contained_path(base_dir, *segments):
	"""Join `segments` under `base_dir`, refusing anything that escapes it.

	Every path this module renames, removes or creates goes through here, so a
	crafted theme name cannot reach a directory outside the themes folder."""
	path = os.path.join(base_dir, *segments)
	if not is_within_directory(base_dir, path):
		frappe.throw(frappe._("Invalid theme path: {0}").format(path))
	return path


def get_app_for_module(module):
	"""App a Module Def belongs to; falls back to the engine app."""
	app = frappe.db.get_value("Module Def", module, "app_name") if module else None
	return app or DEFAULT_THEME_APP


def get_theme_app(theme_name):
	"""App whose files back a theme, resolved via its `module` field."""
	return get_app_for_module(frappe.db.get_value("Buzz Theme", theme_name, "module"))


def get_theme_dir(theme_name):
	"""Absolute path to a theme's private templates: <app>/themes/<slug>."""
	base_dir = os.path.join(frappe.get_app_path(get_theme_app(theme_name)), "themes")
	return get_contained_path(base_dir, frappe.scrub(theme_name))


def get_theme_public_dir(theme_name):
	"""Absolute path to a theme's static assets: <app>/public/themes/<slug>."""
	base_dir = os.path.join(frappe.get_app_path(get_theme_app(theme_name)), "public", "themes")
	return get_contained_path(base_dir, frappe.scrub(theme_name))


def get_theme_export_dir(module, slug):
	"""Absolute path to a theme's exported record folder under its module."""
	return get_contained_path(frappe.get_module_path(module), "buzz_theme", slug)


def scaffold_theme(theme_name, module=None):
	app_path = frappe.get_app_path(get_app_for_module(module))
	slug = frappe.scrub(theme_name)
	theme_dir = get_contained_path(os.path.join(app_path, "themes"), slug)

	if os.path.exists(theme_dir):
		return

	for folder in (
		"pages",
		"components/includes",
		"components/macros",
	):
		os.makedirs(get_contained_path(theme_dir, folder), exist_ok=True)

	theme_public_dir = get_contained_path(os.path.join(app_path, "public", "themes"), slug)
	for folder in ("css", "js", "images"):
		os.makedirs(get_contained_path(theme_public_dir, folder), exist_ok=True)


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


def resolve_theme():
	"""Theme for this render: the previewed theme, else the site default.

	One theme per site, deliberately. Theming an individual event would let a
	listing page and the events it links to render in different design
	languages, which is why hosted platforms attach the theme to the organizer
	or workspace and let an event vary only its content (cover, accent), never
	its templates."""
	return requested_preview_theme() or resolve_default_theme()


def get_theme_context(theme_name):
	"""Resolved chain/dirs/apps for one theme, cached per theme name.

	Keyed per theme rather than as one global entry so that switching the
	default — or previewing a second theme — does not evict the other's chain."""
	if not theme_name:
		return build_theme_context(None)
	return frappe.cache.hget(
		"buzz_theme_context", theme_name, generator=lambda: build_theme_context(theme_name)
	)


def get_render_theme_context():
	"""Theme context for the current render, shared by the renderer and the
	Jinja helpers.

	Both sides call this rather than resolving separately: if they ever
	disagreed, a page would render one theme's markup against another's assets,
	which shows up as a broken stylesheet rather than an error."""
	return get_theme_context(resolve_theme())


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
