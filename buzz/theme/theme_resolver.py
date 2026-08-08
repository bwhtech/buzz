import importlib.util
import os

import frappe
from frappe.utils.jinja import get_jenv
from frappe.utils.jinja_globals import is_rtl
from frappe.website.utils import build_response, get_boot_data
from jinja2 import BaseLoader, TemplateNotFound

from buzz.theme.doctype.buzz_theme.buzz_theme import get_render_theme_context
from buzz.theme.doctype.buzz_theme_settings.buzz_theme_settings import get_compiled_routes


def is_within_directory(directory, target):
	"""True if `target` resolves to a path inside `directory`.

	Guards every lookup that folds a request path or a template-supplied
	include path into a filesystem path: a `..` segment that survives upstream
	normalization must not let a render escape the theme folder (file
	disclosure / SSTI surface). Don't trust werkzeug to have normalized it."""
	directory = os.path.realpath(directory)
	target = os.path.realpath(target)
	return target == directory or target.startswith(directory + os.sep)


def find_theme_file(theme_dirs, relative_path):
	"""First existing, containment-checked file for `relative_path`, walking the
	theme chain child-first. Returns the absolute path or None."""
	for theme_dir in theme_dirs:
		candidate = os.path.join(theme_dir, relative_path)
		if is_within_directory(theme_dir, candidate) and os.path.isfile(candidate):
			return candidate
	return None


# Executed page controllers, keyed by absolute path, each entry carrying the
# mtime it was built from. A bare path -> module dict would pin a theme author's
# first version of the file for the life of the worker; re-executing on every
# request would pay import cost per hit in production.
page_controller_modules = {}


def load_page_controller(theme_dirs, template_relative_path):
	"""Sibling `.py` module for a theme page template, or None if it ships none.

	Mirrors Frappe's `www/` convention (`foo.html` + `foo.py`). The lookup goes
	through `find_theme_file`, so a controller inherits and is containment-checked
	exactly the way its template is."""
	controller_relative_path = f"{os.path.splitext(template_relative_path)[0]}.py"
	controller_path = find_theme_file(theme_dirs, controller_relative_path)
	if not controller_path:
		return None

	modified_time = os.path.getmtime(controller_path)
	cached = page_controller_modules.get(controller_path)
	if cached and cached[0] == modified_time:
		return cached[1]

	module_name = build_controller_module_name(theme_dirs, controller_path, controller_relative_path)
	spec = importlib.util.spec_from_file_location(module_name, controller_path)
	module = importlib.util.module_from_spec(spec)
	# Loaded by file path and kept out of `sys.modules`: a theme folder is not
	# guaranteed to be an importable package, and a theme must never be able to
	# shadow a real app module by picking its name.
	spec.loader.exec_module(module)
	page_controller_modules[controller_path] = (modified_time, module)
	return module


def build_controller_module_name(theme_dirs, controller_path, relative_path):
	"""Import name for a theme page controller: theme slug + its relative path.

	The slug has to be in there because a child theme and its parent may ship the
	same relative path, and the two modules must not end up sharing an identity
	(`__name__` drives tracebacks, `dataclass`/`Enum` registration, pickling)."""
	theme_slug = ""
	for theme_dir in theme_dirs:
		if os.path.join(theme_dir, relative_path) == controller_path:
			theme_slug = os.path.basename(theme_dir.rstrip(os.sep))
			break

	page_slug = os.path.splitext(relative_path)[0]
	for separator in (os.sep, "/", "-", "."):
		page_slug = page_slug.replace(separator, "_")

	return f"buzz.theme.theme_pages.{theme_slug}.{page_slug}"


def run_page_controller(theme_dirs, template_relative_path, context):
	"""Run the page's `get_context(context)`, merging anything it returns.

	Same contract as a `www/` controller (see
	`frappe/website/page_renderers/template_page.py`): the callable may mutate
	the context in place, return a dict, or both. Nothing is caught here on
	purpose — raising `frappe.Redirect`, `frappe.PermissionError` or
	`frappe.DoesNotExistError` is how a controller redirects or 404s, and
	`frappe.website.serve` already turns those into the right response."""
	module = load_page_controller(theme_dirs, template_relative_path)
	if not module or not hasattr(module, "get_context"):
		return

	data = module.get_context(context)
	if data:
		context.update(data)


class ThemePageRenderer:
	def __init__(self, path, http_status_code=None):
		self.path = path
		self.http_status_code = http_status_code
		self.theme_dirs = None
		self.template_path = None
		self.match = None
		self.requires_auth = False

	def can_render(self):
		context = get_render_theme_context()
		if not context["theme_name"]:
			return False

		self.theme_dirs = context["dirs"]
		if not self.theme_dirs:
			return False

		if hasattr(frappe.local, "request") and frappe.local.request:
			request_path = frappe.local.request.path.strip("/")
		else:
			request_path = self.path.strip("/")

		settings = get_compiled_routes()

		# Explicit routes win over dynamic pages; they may also carry auth flags.
		for route in settings["routes"]:
			match = route["pattern"].match(request_path)
			if match:
				if find_theme_file(self.theme_dirs, route["template_path"]):
					self.template_path = route["template_path"]
					self.match = match
					self.requires_auth = route["requires_auth"]
					return True
				return False

		if settings["dynamic_pages_enabled"] and request_path:
			candidate = f"pages/{request_path}.html"
			if find_theme_file(self.theme_dirs, candidate):
				self.template_path = candidate
				self.match = None
				return True

		return False

	def render(self):
		if self.requires_auth and frappe.session.user == "Guest":
			raise frappe.PermissionError

		context = build_base_context(self.match)
		# Last, so a page controller can read and override whatever the host's
		# global hooks put on the context — the same precedence a `www/`
		# controller has over `update_website_context`.
		run_page_controller(self.theme_dirs, self.template_path, context)
		html = self.render_with_theme_loader(context)
		return build_response(self.path, html, self.http_status_code or 200)

	def render_with_theme_loader(self, context):
		jenv = get_jenv()
		theme_env = get_theme_environment(jenv, self.theme_dirs)
		template = theme_env.get_template(f"theme://{self.template_path}", globals=jenv.globals)
		return template.render(context)


class ThemeFallbackLoader(BaseLoader):
	"""Resolves templates through the theme chain, then the host's default
	loader. Owned by a per-chain Jinja environment (see `get_theme_environment`)
	so the loader — and therefore every `{% extends %}`/`{% include %}` lookup a
	cached template performs at render time — stays stable across requests."""

	def __init__(self, theme_dirs, fallback_loader):
		self.theme_dirs = tuple(theme_dirs)
		self.fallback_loader = fallback_loader

	def get_source(self, environment, template):
		if template.startswith("theme://"):
			relative_path = template[len("theme://") :]
			full_path = find_theme_file(self.theme_dirs, relative_path)
			if full_path:
				return read_template_source(full_path)
			raise TemplateNotFound(template)

		relative_path = template
		if relative_path.startswith("templates/"):
			relative_path = relative_path[len("templates/") :]

		for theme_dir in self.theme_dirs:
			for candidate_relative in (relative_path, os.path.join("components", relative_path)):
				candidate = os.path.join(theme_dir, candidate_relative)
				if is_within_directory(theme_dir, candidate) and os.path.isfile(candidate):
					return read_template_source(candidate)

		return self.fallback_loader.get_source(environment, template)


def read_template_source(full_path):
	modified_time = os.path.getmtime(full_path)
	with open(full_path) as source_file:
		source = source_file.read()
	return (
		source,
		full_path,
		lambda path=full_path, modified=modified_time: os.path.getmtime(path) == modified,
	)


# One Jinja environment per theme chain, built once and reused. The host jenv
# is request-local and its loader gets restored after each render, so a
# template compiled under a temporarily-swapped loader would, on a later cache
# hit, resolve its includes/extends against the wrong loader. A dedicated
# overlay env whose loader is permanently the theme loader keeps that
# resolution correct while still letting compiled templates be reused across
# requests (the env — and its own template cache — outlive the request).
theme_environments = {}


def get_theme_environment(jenv, theme_dirs):
	key = tuple(theme_dirs)
	theme_env = theme_environments.get(key)
	if theme_env is None:
		loader = ThemeFallbackLoader(theme_dirs, jenv.loader)
		theme_env = jenv.overlay(loader=loader)
		# The host jenv sidesteps staleness in dev with a per-request cache;
		# this env's cache persists across requests, so let Jinja's mtime check
		# (our loader's `up_to_date` callback) fire to pick up theme-file edits
		# without a restart. A cache hit with an unchanged file still skips
		# recompilation — only the stat is paid, so it's off in production.
		theme_env.auto_reload = bool(frappe.conf.get("developer_mode") or frappe._dev_server)
		theme_environments[key] = theme_env
	return theme_env


def build_base_context(match):
	context = frappe._dict(
		is_rtl=is_rtl(),
		csrf_token=frappe.sessions.get_csrf_token(),
	)

	if match:
		apply_route_groups(match, context)

	try:
		context.boot = get_boot_data()
	except Exception:
		context.boot = {}

	apply_website_context_hooks(context)

	return context


def apply_route_groups(match, context):
	"""Expose a matched route's named groups on the context and in `form_dict`.

	`form_dict` is what makes a host app's existing `www/` controller reusable
	from a theme page: those controllers read their path params from there,
	because Frappe's own `website_route_rules` land them there
	(`frappe.local.form_dict.update(args)` in
	`frappe.website.router.evaluate_dynamic_routes`). Same plain `update` here,
	so — as in Frappe — a route group overwrites a query-string param of the
	same name rather than the other way round."""
	groups = match.groupdict() or {}
	if not groups:
		return

	context.update(groups)
	frappe.local.form_dict.update(groups)


def apply_website_context_hooks(context):
	"""Run the host app's `update_website_context` hooks on a themed page.

	This renderer stands in for Frappe's own page renderers, so nothing else runs
	them here — without this every themed page renders missing the host's
	site-wide globals (title, nav, footer, analytics). Calling convention copied
	from `frappe.website.page_renderers.base_template_page`."""
	for hook_method in frappe.get_hooks("update_website_context"):
		values = frappe.get_attr(hook_method)(context)
		if values:
			context.update(values)
