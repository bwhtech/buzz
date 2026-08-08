import importlib.util
import os

import frappe
from frappe.utils.jinja import get_jenv
from frappe.utils.jinja_globals import is_rtl
from frappe.website.utils import build_response, get_boot_data
from jinja2 import BaseLoader, TemplateNotFound

from buzz.buzz_themes.doctype.buzz_theme.buzz_theme import get_render_theme_context, is_within_directory
from buzz.buzz_themes.doctype.buzz_theme_settings.buzz_theme_settings import get_compiled_routes

RESERVED_PATH_SEGMENTS = frozenset(
	{
		"api",
		"app",
		"assets",
		"b",
		"backups",
		"dashboard",
		"desk",
		"files",
		"login",
		"private",
		"socket.io",
	}
)


def find_theme_file(theme_dirs, relative_path):
	for theme_dir in theme_dirs:
		candidate = os.path.join(theme_dir, relative_path)
		if is_within_directory(theme_dir, candidate) and os.path.isfile(candidate):
			return candidate
	return None


page_controller_modules = {}


def load_page_controller(theme_dirs, template_relative_path):
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
	spec.loader.exec_module(module)
	page_controller_modules[controller_path] = (modified_time, module)
	return module


def build_controller_module_name(theme_dirs, controller_path, relative_path):
	theme_slug = ""
	for theme_dir in theme_dirs:
		if os.path.join(theme_dir, relative_path) == controller_path:
			theme_slug = os.path.basename(theme_dir.rstrip(os.sep))
			break

	page_slug = os.path.splitext(relative_path)[0]
	for separator in (os.sep, "/", "-", "."):
		page_slug = page_slug.replace(separator, "_")

	return f"buzz.buzz_themes.theme_pages.{theme_slug}.{page_slug}"


def run_page_controller(theme_dirs, template_relative_path, context):
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
		if not context["theme_name"] or not context["dirs"]:
			return False

		if hasattr(frappe.local, "request") and frappe.local.request:
			request_path = frappe.local.request.path.strip("/")
		else:
			request_path = self.path.strip("/")

		settings = get_compiled_routes()

		matched_route = None
		match = None
		for route in settings["routes"]:
			candidate = route["pattern"].match(request_path)
			if candidate:
				matched_route = route
				match = candidate
				break

		if matched_route:
			template_path = matched_route["template_path"]
			requires_auth = matched_route["requires_auth"]
		elif (
			settings["dynamic_pages_enabled"]
			and request_path
			and request_path.split("/")[0] not in RESERVED_PATH_SEGMENTS
		):
			template_path = f"pages/{request_path}.html"
			requires_auth = False
		else:
			return False

		if not find_theme_file(context["dirs"], template_path):
			return False

		self.theme_dirs = context["dirs"]
		self.template_path = template_path
		self.match = match
		self.requires_auth = requires_auth
		return True

	def render(self):
		if self.requires_auth and frappe.session.user == "Guest":
			raise frappe.PermissionError

		context = build_base_context(self.match)
		run_page_controller(self.theme_dirs, self.template_path, context)
		html = self.render_with_theme_loader(context)
		return build_response(self.path, html, self.http_status_code or 200)

	def render_with_theme_loader(self, context):
		jenv = get_jenv()
		theme_env = get_theme_environment(jenv, self.theme_dirs)
		template = theme_env.get_template(f"theme://{self.template_path}", globals=jenv.globals)
		return template.render(context)


class ThemeFallbackLoader(BaseLoader):
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
	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-security-file-traversal
	with open(full_path) as source_file:
		source = source_file.read()
	return (
		source,
		full_path,
		lambda path=full_path, modified=modified_time: os.path.getmtime(path) == modified,
	)


theme_environments = {}


def get_theme_environment(jenv, theme_dirs):
	key = tuple(theme_dirs)
	theme_env = theme_environments.get(key)
	if theme_env is None:
		loader = ThemeFallbackLoader(theme_dirs, jenv.loader)
		theme_env = jenv.overlay(loader=loader)
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
		frappe.log_error(title="Buzz Theme: boot data failed")

	apply_website_context_hooks(context)

	return context


def apply_route_groups(match, context):
	groups = match.groupdict() or {}
	if not groups:
		return

	context.update(groups)
	frappe.local.form_dict.update(groups)


def apply_website_context_hooks(context):
	for hook_method in frappe.get_hooks("update_website_context"):
		values = frappe.get_attr(hook_method)(context)
		if values:
			context.update(values)
