import os
import shutil
import tempfile
from contextlib import contextmanager

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import set_request

from buzz.buzz_themes.doctype.buzz_theme.buzz_theme import (
	clear_theme_cache,
	get_render_theme_context,
	get_theme_names,
	is_within_directory,
	validate_theme_name,
)
from buzz.buzz_themes.doctype.buzz_theme_settings.buzz_theme_settings import (
	DEFAULT_ROUTES,
	clear_settings_cache,
	get_compiled_routes,
	seed_default_routes,
)
from buzz.buzz_themes.jinja_helpers import buzz_map_embed_url, buzz_theme_asset_url, buzz_theme_config
from buzz.buzz_themes.theme_resolver import ThemePageRenderer, find_theme_file


@contextmanager
def developer_mode(enabled):
	original_value = frappe.local.conf.get("developer_mode")
	frappe.local.conf.developer_mode = 1 if enabled else 0
	try:
		yield
	finally:
		frappe.local.conf.developer_mode = original_value


def write_theme_file(base_dir, relative_path, content):
	full_path = os.path.join(base_dir, relative_path)
	os.makedirs(os.path.dirname(full_path), exist_ok=True)
	with open(full_path, "w") as target_file:
		target_file.write(content)
	return full_path


class TestThemeNameValidation(UnitTestCase):
	def test_rejects_names_that_could_reach_the_filesystem(self):
		for theme_name in ("../../../evil name", "..", "a/../b", "<script>", "", None):
			with self.subTest(theme_name=theme_name), self.assertRaises(frappe.ValidationError):
				validate_theme_name(theme_name)

	def test_accepts_plain_theme_names(self):
		for theme_name in ("Stickerpack Theme", "My-Theme_2"):
			with self.subTest(theme_name=theme_name):
				validate_theme_name(theme_name)


class TestPathContainment(UnitTestCase):
	def setUp(self):
		super().setUp()
		self.base_dir = tempfile.mkdtemp()
		self.addCleanup(shutil.rmtree, self.base_dir, True)
		self.theme_dir = os.path.join(self.base_dir, "themes", "foo")
		os.makedirs(os.path.join(self.theme_dir, "pages"))

	def test_accepts_nested_path(self):
		self.assertTrue(is_within_directory(self.theme_dir, os.path.join(self.theme_dir, "pages/home.html")))

	def test_accepts_the_directory_itself(self):
		self.assertTrue(is_within_directory(self.theme_dir, self.theme_dir))

	def test_rejects_parent_escape(self):
		escaping_path = os.path.join(self.theme_dir, "../../secrets.txt")
		self.assertFalse(is_within_directory(self.theme_dir, escaping_path))

	def test_rejects_sibling_with_same_prefix(self):
		sibling_dir = os.path.join(self.base_dir, "themes", "foo-evil")
		self.assertFalse(is_within_directory(self.theme_dir, sibling_dir))

	def test_find_theme_file_refuses_traversal(self):
		write_theme_file(self.base_dir, "outside.html", "leak")
		self.assertIsNone(find_theme_file([self.theme_dir], "../outside.html"))

	def test_find_theme_file_returns_child_before_parent(self):
		parent_dir = os.path.join(self.base_dir, "themes", "parent")
		child_path = write_theme_file(self.theme_dir, "pages/home.html", "child")
		write_theme_file(parent_dir, "pages/home.html", "parent")

		self.assertEqual(find_theme_file([self.theme_dir, parent_dir], "pages/home.html"), child_path)

	def test_find_theme_file_falls_through_to_parent(self):
		parent_dir = os.path.join(self.base_dir, "themes", "parent")
		parent_path = write_theme_file(parent_dir, "pages/about.html", "parent")

		self.assertEqual(find_theme_file([self.theme_dir, parent_dir], "pages/about.html"), parent_path)

	def test_find_theme_file_returns_none_when_missing(self):
		self.assertIsNone(find_theme_file([self.theme_dir], "pages/nope.html"))


class ThemeEngineTestCase(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.created_theme_names = []
		self.created_dirs = []
		self.original_default_theme = frappe.db.get_single_value("Buzz Settings", "default_theme")
		clear_theme_cache()
		clear_settings_cache()

	def tearDown(self):
		for theme_name in reversed(self.created_theme_names):
			if frappe.db.exists("Buzz Theme", theme_name):
				with developer_mode(False):
					frappe.delete_doc("Buzz Theme", theme_name, force=True, ignore_permissions=True)

		for directory in self.created_dirs:
			shutil.rmtree(directory, ignore_errors=True)

		self.set_default_theme(self.original_default_theme)
		frappe.clear_document_cache("Buzz Theme Settings", "Buzz Theme Settings")
		clear_settings_cache()
		clear_theme_cache()

		if getattr(frappe.local, "request", None) is not None:
			del frappe.local.request
		frappe.set_user("Administrator")
		super().tearDown()

	def create_theme(self, parent_theme=None, is_standard=0, templates=None, assets=None):
		theme_name = f"Ztest Theme {frappe.generate_hash(length=8)}"

		with developer_mode(False):
			theme = frappe.new_doc("Buzz Theme")
			theme.theme_name = theme_name
			theme.module = "Buzz Themes"
			theme.parent_theme = parent_theme
			theme.is_standard = is_standard
			theme.insert()

		self.created_theme_names.append(theme.name)
		self.register_theme_dirs(theme.name)

		for relative_path, content in (templates or {}).items():
			write_theme_file(self.theme_dir(theme.name), relative_path, content)
		for relative_path, content in (assets or {}).items():
			write_theme_file(self.theme_public_dir(theme.name), relative_path, content)

		clear_theme_cache()
		return theme

	def theme_dir(self, theme_name):
		return os.path.join(frappe.get_app_path("buzz"), "themes", frappe.scrub(theme_name))

	def theme_public_dir(self, theme_name):
		return os.path.join(frappe.get_app_path("buzz"), "public", "themes", frappe.scrub(theme_name))

	def register_theme_dirs(self, theme_name):
		for directory in (self.theme_dir(theme_name), self.theme_public_dir(theme_name)):
			os.makedirs(directory, exist_ok=True)
			self.created_dirs.append(directory)

	def set_default_theme(self, theme_name):
		frappe.db.set_single_value("Buzz Settings", "default_theme", theme_name)
		frappe.clear_document_cache("Buzz Settings", "Buzz Settings")
		clear_theme_cache()

	def set_routes(self, routes, dynamic_pages_enabled=1):
		settings = frappe.get_doc("Buzz Theme Settings")
		settings.dynamic_pages_enabled = dynamic_pages_enabled
		settings.routes = []
		for url_pattern, template_path, requires_auth in routes:
			settings.append(
				"routes",
				{
					"url_pattern": url_pattern,
					"template_path": template_path,
					"requires_auth": requires_auth,
				},
			)
		settings.save()
		return settings

	def make_renderer(self, path):
		set_request(method="GET", path=f"/{path}")
		return ThemePageRenderer(path)


class TestMapEmbedUrl(UnitTestCase):
	def test_extracts_src_from_a_pasted_google_iframe(self):
		embed_code = (
			'<iframe src="https://www.google.com/maps/embed?pb=!1m18!2sfoo" '
			'width="600" height="450" style="border:0;" allowfullscreen></iframe>'
		)
		self.assertEqual(buzz_map_embed_url(embed_code), "https://www.google.com/maps/embed?pb=!1m18!2sfoo")

	def test_accepts_a_bare_embed_url(self):
		url = "https://www.google.com/maps/embed?pb=!1m18"
		self.assertEqual(buzz_map_embed_url(url), url)

	def test_rejects_markup_that_is_not_a_google_embed(self):
		attacks = (
			'<iframe src="https://evil.example/pwn"></iframe>',
			'<img src=x onerror="alert(1)">',
			"<script>alert(1)</script>",
			'<iframe src="javascript:alert(1)"></iframe>',
			'<iframe src="data:text/html,<script>alert(1)</script>"></iframe>',
			"https://evil.example/maps/embed",
			"javascript:alert(1)",
		)
		for embed_code in attacks:
			with self.subTest(embed_code=embed_code):
				self.assertEqual(buzz_map_embed_url(embed_code), "")

	def test_rejects_a_google_lookalike_host(self):
		self.assertEqual(
			buzz_map_embed_url('<iframe src="https://www.google.com.evil.example/maps/embed"></iframe>'), ""
		)

	def test_empty_input_is_empty_output(self):
		for embed_code in ("", None, "   "):
			with self.subTest(embed_code=embed_code):
				self.assertEqual(buzz_map_embed_url(embed_code), "")


class TestThemeAssetUrl(ThemeEngineTestCase):
	def test_asset_url_points_at_the_active_theme(self):
		theme = self.create_theme(assets={"tailwind.output.css": "body{}"})
		self.set_default_theme(theme.name)

		self.assertEqual(
			buzz_theme_asset_url("tailwind.output.css"),
			f"/assets/buzz/themes/{frappe.scrub(theme.name)}/tailwind.output.css",
		)

	def test_leading_slash_is_normalised(self):
		theme = self.create_theme(assets={"scripts/app.js": "// noop"})
		self.set_default_theme(theme.name)

		self.assertEqual(
			buzz_theme_asset_url("/scripts/app.js"),
			f"/assets/buzz/themes/{frappe.scrub(theme.name)}/scripts/app.js",
		)

	def test_missing_asset_falls_back_to_base_theme_url(self):
		theme = self.create_theme()
		self.set_default_theme(theme.name)

		self.assertEqual(
			buzz_theme_asset_url("images/logo.svg"),
			f"/assets/buzz/themes/{frappe.scrub(theme.name)}/images/logo.svg",
		)

	def test_child_theme_asset_overrides_parent(self):
		parent_theme = self.create_theme(assets={"tailwind.output.css": "parent"})
		child_theme = self.create_theme(
			parent_theme=parent_theme.name, assets={"tailwind.output.css": "child"}
		)
		self.set_default_theme(child_theme.name)

		self.assertEqual(
			buzz_theme_asset_url("tailwind.output.css"),
			f"/assets/buzz/themes/{frappe.scrub(child_theme.name)}/tailwind.output.css",
		)

	def test_parent_asset_is_used_when_child_ships_none(self):
		parent_theme = self.create_theme(assets={"tailwind.output.css": "parent"})
		child_theme = self.create_theme(parent_theme=parent_theme.name)
		self.set_default_theme(child_theme.name)

		self.assertEqual(
			buzz_theme_asset_url("tailwind.output.css"),
			f"/assets/buzz/themes/{frappe.scrub(parent_theme.name)}/tailwind.output.css",
		)

	def test_asset_url_is_empty_without_a_configured_theme(self):
		self.set_default_theme(None)
		self.assertEqual(buzz_theme_asset_url("tailwind.output.css"), "")


class TestThemeInheritance(ThemeEngineTestCase):
	def test_chain_is_resolved_child_first(self):
		grandparent_theme = self.create_theme()
		parent_theme = self.create_theme(parent_theme=grandparent_theme.name)
		child_theme = self.create_theme(parent_theme=parent_theme.name)

		self.assertEqual(
			get_theme_names(child_theme.name),
			[child_theme.name, parent_theme.name, grandparent_theme.name],
		)

	def test_template_only_in_parent_is_found(self):
		parent_theme = self.create_theme(templates={"pages/about.html": "<h1>Parent About</h1>"})
		child_theme = self.create_theme(parent_theme=parent_theme.name)
		self.set_default_theme(child_theme.name)

		context = get_render_theme_context()
		self.assertEqual(
			find_theme_file(context["dirs"], "pages/about.html"),
			os.path.join(self.theme_dir(parent_theme.name), "pages/about.html"),
		)

	def test_circular_inheritance_is_rejected(self):
		first_theme = self.create_theme()
		second_theme = self.create_theme(parent_theme=first_theme.name)

		first_theme.parent_theme = second_theme.name
		with self.assertRaises(frappe.ValidationError):
			first_theme.save()


class TestCanRender(ThemeEngineTestCase):
	def test_declines_when_no_theme_is_configured(self):
		self.set_default_theme(None)
		self.set_routes([("^probe$", "pages/probe.html", 0)])

		self.assertFalse(self.make_renderer("probe").can_render())

	def test_explicit_route_selects_its_template(self):
		theme = self.create_theme(templates={"pages/events/detail.html": "<h1>Detail</h1>"})
		self.set_default_theme(theme.name)
		self.set_routes([(r"^events/(?P<event_route>[^/]+)$", "pages/events/detail.html", 0)])

		renderer = self.make_renderer("events/foss-event")
		self.assertTrue(renderer.can_render())
		self.assertEqual(renderer.template_path, "pages/events/detail.html")
		self.assertEqual(renderer.match.group("event_route"), "foss-event")

	def test_explicit_route_with_missing_template_does_not_fall_through(self):
		theme = self.create_theme(templates={"pages/probe.html": "<h1>Dynamic</h1>"})
		self.set_default_theme(theme.name)
		self.set_routes([("^probe$", "pages/gone.html", 0)], dynamic_pages_enabled=1)

		self.assertFalse(self.make_renderer("probe").can_render())

	def test_dynamic_page_is_served_when_enabled(self):
		theme = self.create_theme(templates={"pages/guide/intro.html": "<h1>Intro</h1>"})
		self.set_default_theme(theme.name)
		self.set_routes([], dynamic_pages_enabled=1)

		renderer = self.make_renderer("guide/intro")
		self.assertTrue(renderer.can_render())
		self.assertEqual(renderer.template_path, "pages/guide/intro.html")

	def test_dynamic_page_declines_when_disabled(self):
		theme = self.create_theme(templates={"pages/guide/intro.html": "<h1>Intro</h1>"})
		self.set_default_theme(theme.name)
		self.set_routes([], dynamic_pages_enabled=0)

		self.assertFalse(self.make_renderer("guide/intro").can_render())

	def test_reserved_first_segments_are_never_hijacked(self):
		reserved_paths = ("login", "app", "app/buzz-event", "api/method/ping", "assets/buzz/x.css", "desk")
		templates = {f"pages/{path}.html": "<h1>Hijacked</h1>" for path in reserved_paths}
		theme = self.create_theme(templates=templates)
		self.set_default_theme(theme.name)
		self.set_routes([], dynamic_pages_enabled=1)

		for path in reserved_paths:
			with self.subTest(path=path):
				self.assertFalse(self.make_renderer(path).can_render())

	def test_dynamic_page_cannot_escape_the_pages_directory(self):
		theme = self.create_theme(
			templates={
				"pages/home.html": "<h1>Home</h1>",
				"components/secret_partial.html": "<h1>Partial</h1>",
			}
		)
		self.set_default_theme(theme.name)
		self.set_routes([], dynamic_pages_enabled=1)

		for path in ("../components/secret_partial", "home/../../components/secret_partial"):
			with self.subTest(path=path):
				self.assertFalse(self.make_renderer(path).can_render())

	def test_dynamic_page_rejects_unsafe_segments(self):
		theme = self.create_theme(templates={"pages/home.html": "<h1>Home</h1>"})
		self.set_default_theme(theme.name)
		self.set_routes([], dynamic_pages_enabled=1)

		for path in ("ho me", "home$", "home;x", "ho%me"):
			with self.subTest(path=path):
				self.assertFalse(self.make_renderer(path).can_render())

	def test_dynamic_page_inherits_requires_auth_from_a_route_on_the_same_template(self):
		theme = self.create_theme(templates={"pages/user/account.html": "<h1>Secret</h1>"})
		self.set_default_theme(theme.name)
		self.set_routes([("^account$", "pages/user/account.html", 1)], dynamic_pages_enabled=1)

		renderer = self.make_renderer("user/account")
		self.assertTrue(renderer.can_render())
		self.assertTrue(renderer.requires_auth)

		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			renderer.render()

	def test_non_reserved_lookalike_segment_still_renders(self):
		theme = self.create_theme(templates={"pages/application.html": "<h1>Application</h1>"})
		self.set_default_theme(theme.name)
		self.set_routes([], dynamic_pages_enabled=1)

		self.assertTrue(self.make_renderer("application").can_render())


class TestRender(ThemeEngineTestCase):
	def test_matched_route_renders_the_theme_template(self):
		theme = self.create_theme(templates={"pages/events/detail.html": "<h1>Event {{ event_route }}</h1>"})
		self.set_default_theme(theme.name)
		self.set_routes([(r"^events/(?P<event_route>[^/]+)$", "pages/events/detail.html", 0)])

		renderer = self.make_renderer("events/foss-event")
		self.assertTrue(renderer.can_render())
		response = renderer.render()

		self.assertEqual(response.status_code, 200)
		self.assertIn("Event foss-event", response.get_data(as_text=True))

	def test_child_template_overrides_parent_at_render_time(self):
		parent_theme = self.create_theme(templates={"pages/home.html": "<h1>Parent Home</h1>"})
		child_theme = self.create_theme(
			parent_theme=parent_theme.name, templates={"pages/home.html": "<h1>Child Home</h1>"}
		)
		self.set_default_theme(child_theme.name)
		self.set_routes([("^home$", "pages/home.html", 0)])

		renderer = self.make_renderer("home")
		self.assertTrue(renderer.can_render())

		self.assertIn("Child Home", renderer.render().get_data(as_text=True))

	def test_requires_auth_route_rejects_guest(self):
		theme = self.create_theme(templates={"pages/account.html": "<h1>Account</h1>"})
		self.set_default_theme(theme.name)
		self.set_routes([("^account$", "pages/account.html", 1)])

		renderer = self.make_renderer("account")
		self.assertTrue(renderer.can_render())

		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			renderer.render()

	def test_requires_auth_route_renders_for_logged_in_user(self):
		theme = self.create_theme(templates={"pages/account.html": "<h1>Account</h1>"})
		self.set_default_theme(theme.name)
		self.set_routes([("^account$", "pages/account.html", 1)])

		renderer = self.make_renderer("account")
		self.assertTrue(renderer.can_render())

		self.assertIn("Account", renderer.render().get_data(as_text=True))


class TestRouteValidation(ThemeEngineTestCase):
	def test_invalid_regex_is_rejected_on_save(self):
		with self.assertRaises(frappe.ValidationError):
			self.set_routes([("^events/(?P<slug>[^/]+$", "pages/events/detail.html", 0)])

	def test_saving_settings_invalidates_the_compiled_routes_cache(self):
		self.set_routes([("^first$", "pages/first.html", 0)])
		self.assertEqual(
			[route["template_path"] for route in get_compiled_routes()["routes"]], ["pages/first.html"]
		)

		self.set_routes([("^second$", "pages/second.html", 0)])
		self.assertEqual(
			[route["template_path"] for route in get_compiled_routes()["routes"]], ["pages/second.html"]
		)

	def test_dynamic_pages_flag_is_carried_into_compiled_routes(self):
		self.set_routes([], dynamic_pages_enabled=0)
		self.assertFalse(get_compiled_routes()["dynamic_pages_enabled"])

		self.set_routes([], dynamic_pages_enabled=1)
		self.assertTrue(get_compiled_routes()["dynamic_pages_enabled"])


class TestThemeCacheInvalidation(ThemeEngineTestCase):
	def test_changing_default_theme_changes_the_render_context(self):
		first_theme = self.create_theme()
		second_theme = self.create_theme()

		self.set_default_theme(first_theme.name)
		self.assertEqual(get_render_theme_context()["theme_name"], first_theme.name)

		self.set_default_theme(second_theme.name)
		self.assertEqual(get_render_theme_context()["theme_name"], second_theme.name)
		self.assertEqual(get_render_theme_context()["dirs"], [self.theme_dir(second_theme.name)])

	def test_adding_a_parent_theme_refreshes_the_cached_chain(self):
		parent_theme = self.create_theme()
		child_theme = self.create_theme()
		self.set_default_theme(child_theme.name)

		self.assertEqual(get_render_theme_context()["names"], [child_theme.name])

		child_theme.parent_theme = parent_theme.name
		child_theme.save()

		self.assertEqual(get_render_theme_context()["names"], [child_theme.name, parent_theme.name])


class TestOnTrash(ThemeEngineTestCase):
	def test_standard_theme_files_survive_a_delete(self):
		theme = self.create_theme(is_standard=1, templates={"pages/home.html": "<h1>Shipped</h1>"})
		theme_dir = self.theme_dir(theme.name)

		with developer_mode(True):
			frappe.delete_doc("Buzz Theme", theme.name, force=True)

		self.assertTrue(os.path.isdir(theme_dir))
		self.assertTrue(os.path.isfile(os.path.join(theme_dir, "pages/home.html")))

	def test_non_standard_theme_files_are_removed_in_developer_mode(self):
		theme = self.create_theme(is_standard=0, templates={"pages/home.html": "<h1>Scaffolded</h1>"})
		theme_dir = self.theme_dir(theme.name)

		with developer_mode(True):
			frappe.delete_doc("Buzz Theme", theme.name, force=True)

		self.assertFalse(os.path.isdir(theme_dir))

	def test_non_standard_theme_files_survive_outside_developer_mode(self):
		theme = self.create_theme(is_standard=0, templates={"pages/home.html": "<h1>Site data</h1>"})
		theme_dir = self.theme_dir(theme.name)

		with developer_mode(False):
			frappe.delete_doc("Buzz Theme", theme.name, force=True)

		self.assertTrue(os.path.isdir(theme_dir))


class TestNavLinkValidation(IntegrationTestCase):
	def make_nav_link(self, url):
		return frappe.get_doc({"doctype": "Buzz Theme Nav Link", "label": "Somewhere", "url": url})

	def test_site_relative_path_is_accepted(self):
		self.make_nav_link("/b/event-proposal").validate()

	def test_https_url_is_accepted(self):
		self.make_nav_link("https://example.com/docs").validate()

	def test_javascript_scheme_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_nav_link("javascript:alert(1)").validate()

	def test_data_scheme_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_nav_link("data:text/html,<script>alert(1)</script>").validate()


class TestDefaultThemeNavLinks(IntegrationTestCase):
	def setUp(self):
		self.settings = frappe.get_doc("Buzz Default Theme Settings")
		self.addCleanup(self.restore_nav_links, list(self.settings.nav_links))
		self.settings.set("nav_links", [])

	def restore_nav_links(self, original_rows):
		settings = frappe.get_doc("Buzz Default Theme Settings")
		settings.set("nav_links", [])
		for row in original_rows:
			settings.append(
				"nav_links", {"label": row.label, "url": row.url, "open_in_new_tab": row.open_in_new_tab}
			)
		settings.save()
		frappe.db.commit()

	def test_empty_table_falls_back_to_bundled_links(self):
		links = self.settings.get_nav_links()

		self.assertEqual([link.label for link in links], ["Dashboard", "Propose Event"])
		self.assertEqual([link.url for link in links], ["/b", "/b/event-proposal"])

	def test_configured_links_replace_the_fallback_entirely(self):
		self.settings.append("nav_links", {"label": "Events", "url": "/category/conferences"})

		links = self.settings.get_nav_links()

		self.assertEqual([link.label for link in links], ["Events"])

	def test_configured_link_keeps_the_new_tab_flag(self):
		self.settings.append(
			"nav_links", {"label": "Docs", "url": "https://example.com", "open_in_new_tab": 1}
		)

		self.assertTrue(self.settings.get_nav_links()[0].open_in_new_tab)


class TestThemeConfigHelper(ThemeEngineTestCase):
	def test_config_returns_the_linked_settings_single(self):
		theme = self.create_theme()
		frappe.db.set_value("Buzz Theme", theme.name, "theme_settings", "Buzz Default Theme Settings")
		clear_theme_cache()
		self.set_default_theme(theme.name)

		self.assertEqual(buzz_theme_config().doctype, "Buzz Default Theme Settings")

	def test_config_is_an_empty_dict_when_no_settings_are_linked(self):
		theme = self.create_theme()
		self.set_default_theme(theme.name)

		self.assertEqual(buzz_theme_config(), frappe._dict())


class TestDefaultRouteSeeding(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_single("Buzz Theme Settings")
		self.addCleanup(self.restore_routes, [row.as_dict() for row in settings.routes])

	def restore_routes(self, original_rows):
		settings = frappe.get_single("Buzz Theme Settings")
		settings.set("routes", [])
		for row in original_rows:
			settings.append("routes", row)
		settings.save(ignore_permissions=True)

	def current_patterns(self):
		return [row.url_pattern for row in frappe.get_single("Buzz Theme Settings").routes]

	def test_seeding_an_empty_settings_adds_every_default_route(self):
		settings = frappe.get_single("Buzz Theme Settings")
		settings.set("routes", [])
		settings.save(ignore_permissions=True)

		seed_default_routes()

		self.assertEqual(self.current_patterns(), [route["url_pattern"] for route in DEFAULT_ROUTES])

	def test_seeding_twice_does_not_duplicate_routes(self):
		seed_default_routes()
		patterns_after_first_run = self.current_patterns()

		seed_default_routes()

		self.assertEqual(self.current_patterns(), patterns_after_first_run)

	def test_seeding_preserves_custom_routes(self):
		settings = frappe.get_single("Buzz Theme Settings")
		settings.set("routes", [])
		settings.append(
			"routes",
			{"url_pattern": "^sponsors$", "template_path": "pages/sponsors.html", "requires_auth": 0},
		)
		settings.save(ignore_permissions=True)

		seed_default_routes()

		self.assertIn("^sponsors$", self.current_patterns())
		self.assertIn("^home$", self.current_patterns())
