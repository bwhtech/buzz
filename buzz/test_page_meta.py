# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.page_meta import DEFAULT_TITLE, get_page_meta


def ensure_prompt_named_record(doctype, name):
	# Event Category / Event Host use autoname "prompt" -> name set explicitly.
	if frappe.db.exists(doctype, name):
		return name
	doc = frappe.new_doc(doctype)
	doc.name = name
	doc.insert(ignore_permissions=True)
	return doc.name


class TestPageMeta(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Test Page Meta Category")
		cls.host = ensure_prompt_named_record("Event Host", "Test Page Meta Host")

	def make_event(self, is_published=1, route=None, form_route=None, publish_form=1, **kwargs):
		event = frappe.new_doc("Buzz Event")
		event.update(
			{
				"title": f"Test Event {frappe.generate_hash(length=6)}",
				"start_date": "2030-01-01",
				"end_date": "2030-01-01",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"category": self.category,
				"host": self.host,
				"is_published": is_published,
			}
		)
		if route:
			event.route = route
		event.update(kwargs)
		event.set("custom_forms", [])
		if form_route:
			event.append(
				"custom_forms",
				{"form_doctype": "Talk Proposal", "route": form_route, "publish": publish_form},
			)
		event.insert(ignore_permissions=True)
		event.reload()
		return event


class TestRegisterPageMeta(TestPageMeta):
	def test_title_has_event_name(self):
		event = self.make_event()
		meta = get_page_meta(f"register/{event.route}")
		self.assertIn(event.title, meta["title"])
		self.assertIn("Register", meta["title"])

	def test_short_description_used_as_description(self):
		event = self.make_event(short_description="Three days of Frappe talks.")
		meta = get_page_meta(f"register/{event.route}")
		self.assertEqual(meta["description"], "Three days of Frappe talks.")

	def test_description_falls_back_to_title(self):
		event = self.make_event()
		meta = get_page_meta(f"register/{event.route}")
		self.assertEqual(meta["description"], meta["title"])

	def test_image_is_absolute_url(self):
		event = self.make_event(meta_image="/files/meta.png")
		meta = get_page_meta(f"register/{event.route}")
		self.assertTrue(meta["image"].startswith("http"))
		self.assertTrue(meta["image"].endswith("/files/meta.png"))

	def test_banner_image_used_when_no_meta_image(self):
		event = self.make_event(banner_image="/files/banner.png")
		meta = get_page_meta(f"register/{event.route}")
		self.assertTrue(meta["image"].endswith("/files/banner.png"))

	def test_no_image_returns_empty_string(self):
		event = self.make_event()
		meta = get_page_meta(f"register/{event.route}")
		self.assertEqual(meta["image"], "")

	def test_unpublished_event_title_does_not_leak(self):
		event = self.make_event(is_published=0, route="unpublished-page-meta-event")
		meta = get_page_meta(f"register/{event.route}")
		self.assertEqual(meta["title"], DEFAULT_TITLE)
		self.assertNotIn(event.title, meta["title"])

	def test_unknown_event_route_returns_default(self):
		meta = get_page_meta("register/no-such-event")
		self.assertEqual(meta["title"], DEFAULT_TITLE)


class TestCustomFormPageMeta(TestPageMeta):
	def test_title_has_event_name_and_form(self):
		event = self.make_event(form_route="talks")
		meta = get_page_meta(f"{event.route}/talks")
		self.assertIn(event.title, meta["title"])
		self.assertIn("Talk Proposal", meta["title"])

	def test_unpublished_form_returns_default(self):
		event = self.make_event(form_route="talks", publish_form=0)
		meta = get_page_meta(f"{event.route}/talks")
		self.assertEqual(meta["title"], DEFAULT_TITLE)

	def test_unknown_form_route_returns_default(self):
		event = self.make_event(form_route="talks")
		meta = get_page_meta(f"{event.route}/no-such-form")
		self.assertEqual(meta["title"], DEFAULT_TITLE)

	def test_unpublished_event_form_returns_default(self):
		event = self.make_event(is_published=0, route="unpublished-form-page-meta-event", form_route="talks")
		meta = get_page_meta(f"{event.route}/talks")
		self.assertEqual(meta["title"], DEFAULT_TITLE)

	def test_reserved_route_is_not_treated_as_event(self):
		# /b/account/bookings is an app route, not <event>/<form>.
		meta = get_page_meta("account/bookings")
		self.assertEqual(meta["title"], DEFAULT_TITLE)


class TestEventProposalPageMeta(TestPageMeta):
	def set_banner_title(self, title):
		# set_single_value over save(): Buzz Settings has unrelated mandatory
		# fields, and this clears the single-value cache get_page_meta reads.
		frappe.db.set_single_value("Buzz Settings", "event_proposal_banner_title", title)

	def test_banner_title_from_settings(self):
		self.set_banner_title("Host a Buzz Event")
		meta = get_page_meta("event-proposal")
		self.assertEqual(meta["title"], "Host a Buzz Event")

	def test_falls_back_when_banner_title_blank(self):
		self.set_banner_title("")
		meta = get_page_meta("event-proposal")
		self.assertEqual(meta["title"], "Propose an Event")


class TestFallbackPageMeta(TestPageMeta):
	def test_no_app_path_returns_default(self):
		for app_path in (None, "", "/"):
			self.assertEqual(get_page_meta(app_path)["title"], DEFAULT_TITLE)

	def test_account_route_returns_default(self):
		self.assertEqual(get_page_meta("account/tickets/TKT-0001")["title"], DEFAULT_TITLE)

	def test_default_meta_is_never_empty_title(self):
		meta = get_page_meta("check-in")
		self.assertEqual(meta["title"], DEFAULT_TITLE)
		self.assertEqual(meta["description"], DEFAULT_TITLE)
		self.assertEqual(meta["image"], "")
