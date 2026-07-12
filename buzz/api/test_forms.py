import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.forms import (
	STANDARD_EXCLUDE_FIELDS,
	get_custom_form_data,
	get_form_fields,
	get_link_field_options,
	parse_excluded_fields,
	submit_custom_form,
	validate_excluded_fields,
)

# Renderable Talk Proposal fields (after STANDARD_EXCLUDE_FIELDS + auto-set event/submitted_by):
#   title (reqd, Data), description (Text Editor), speakers (reqd, Table), phone (Phone)
TALK_PROPOSAL_EXCLUDE = STANDARD_EXCLUDE_FIELDS | {"event", "submitted_by"}


def ensure_prompt_named_record(doctype, name):
	# Event Category / Event Host use autoname "prompt" -> name set explicitly.
	if frappe.db.exists(doctype, name):
		return name
	doc = frappe.new_doc(doctype)
	doc.name = name
	doc.insert(ignore_permissions=True)
	return doc.name


class TestParseExcludedFields(IntegrationTestCase):
	def test_blank_returns_none(self):
		self.assertIsNone(parse_excluded_fields(None))
		self.assertIsNone(parse_excluded_fields(""))
		self.assertIsNone(parse_excluded_fields("   "))
		self.assertIsNone(parse_excluded_fields(", ,,"))

	def test_trims_and_drops_empties(self):
		self.assertEqual(parse_excluded_fields("a, b ,,c"), {"a", "b", "c"})

	def test_single_field(self):
		self.assertEqual(parse_excluded_fields("title"), {"title"})


class TestGetFormFields(IntegrationTestCase):
	def test_excluding_a_field_drops_it(self):
		exclude_fields = TALK_PROPOSAL_EXCLUDE | {"phone"}
		fields = get_form_fields("Talk Proposal", exclude_fields)
		returned = {f["fieldname"] for f in fields}
		self.assertNotIn("phone", returned)
		self.assertTrue({"title", "description", "speakers"} <= returned)

	def test_no_extra_exclude_returns_all_renderable(self):
		fields = get_form_fields("Talk Proposal", TALK_PROPOSAL_EXCLUDE)
		returned = {f["fieldname"] for f in fields}
		self.assertTrue({"title", "description", "speakers", "phone"} <= returned)

	def test_layout_breaks_pass_through(self):
		# With layout breaks on, section/column breaks are emitted even when other fields are excluded.
		exclude_fields = TALK_PROPOSAL_EXCLUDE | {"description", "speakers", "phone"}
		fields = get_form_fields("Talk Proposal", exclude_fields, with_layout_breaks=True)
		real_fields = {
			f["fieldname"] for f in fields if f["fieldtype"] not in ("Section Break", "Column Break")
		}
		breaks = [f for f in fields if f["fieldtype"] in ("Section Break", "Column Break")]
		self.assertIn("title", real_fields)
		self.assertFalse({"description", "speakers", "phone"} & real_fields)
		self.assertTrue(breaks, "expected layout breaks to pass through")


class TestGetLinkFieldOptions(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Test Forms Category")
		cls.host = ensure_prompt_named_record("Event Host", "Test Forms Host")

	def make_tier(self, title="Gold Tier"):
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
			}
		)
		event.insert(ignore_permissions=True)
		tier = frappe.new_doc("Sponsorship Tier")
		tier.update({"event": event.name, "title": title, "price": 1000, "currency": "INR"})
		tier.insert(ignore_permissions=True)
		return tier

	def test_options_have_value_label_shape(self):
		options = get_link_field_options("Event Host")
		self.assertTrue(options)
		self.assertTrue(all(set(option) == {"value", "label"} for option in options))

	def test_no_title_field_label_falls_back_to_name(self):
		# Event Host has no title field -> label mirrors the name.
		match = next(o for o in get_link_field_options("Event Host") if o["value"] == self.host)
		self.assertEqual(match["label"], self.host)

	def test_title_field_used_as_label(self):
		# Sponsorship Tier names are hashes; its title field is the readable label.
		tier = self.make_tier(title="Gold Tier")
		match = next(o for o in get_link_field_options("Sponsorship Tier") if o["value"] == tier.name)
		self.assertEqual(match["label"], "Gold Tier")
		self.assertNotEqual(match["value"], match["label"])

	def test_null_title_falls_back_to_name(self):
		tier = self.make_tier()
		# Blank the title directly (bypasses the reqd validation) to exercise the fallback.
		frappe.db.set_value("Sponsorship Tier", tier.name, "title", "")
		match = next(o for o in get_link_field_options("Sponsorship Tier") if o["value"] == tier.name)
		self.assertEqual(match["label"], tier.name)


class TestCustomFormExcludedFields(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Test Forms Category")
		cls.host = ensure_prompt_named_record("Event Host", "Test Forms Host")

	def make_event(self, excluded_fields, form_route=None, publish=1):
		form_route = form_route or f"propose-{frappe.generate_hash(length=6)}"
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
				"is_published": 1,
			}
		)
		event.set("custom_forms", [])
		event.append(
			"custom_forms",
			{
				"form_doctype": "Talk Proposal",
				"route": form_route,
				"publish": publish,
				"excluded_fields": excluded_fields,
			},
		)
		event.insert(ignore_permissions=True)
		event.reload()
		return event, form_route

	def test_get_custom_form_data_hides_excluded_fields(self):
		event, form_route = self.make_event("phone")
		data = get_custom_form_data(event.route, form_route)
		returned = {f["fieldname"] for f in data["form_fields"]}
		self.assertNotIn("phone", returned)
		self.assertTrue({"title", "description", "speakers"} <= returned)

	def test_get_custom_form_data_empty_excluded_fields_returns_all(self):
		event, form_route = self.make_event("")
		data = get_custom_form_data(event.route, form_route)
		returned = {f["fieldname"] for f in data["form_fields"]}
		self.assertTrue({"title", "description", "speakers", "phone"} <= returned)

	def test_submit_drops_excluded_field_value(self):
		# phone is excluded -> a posted phone value must be dropped.
		event, form_route = self.make_event("phone")
		submit_custom_form(
			event.route,
			form_route,
			data={
				"title": "Hidden Phone Test",
				"description": "<p>desc</p>",
				"speakers": [{"first_name": "Jane", "email": "jane@example.com"}],
				"phone": "+919999999999",
			},
		)
		created = frappe.get_last_doc("Talk Proposal", filters={"title": "Hidden Phone Test"})
		self.assertEqual(str(created.event), str(event.name))
		self.assertFalse(created.phone, f"phone should be dropped but was {created.phone!r}")
		# Non-excluded fields (and child rows) must still be written.
		self.assertEqual(created.title, "Hidden Phone Test")
		self.assertEqual(created.description, "<p>desc</p>")
		self.assertEqual(len(created.speakers), 1)
		self.assertEqual(created.speakers[0].first_name, "Jane")
		self.assertEqual(created.speakers[0].email, "jane@example.com")


class TestCustomFormLinkEventFilter(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Test Forms Category")
		cls.host = ensure_prompt_named_record("Event Host", "Test Forms Host")

	def make_sponsorship_event(self):
		form_route = f"sponsor-{frappe.generate_hash(length=6)}"
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
				"is_published": 1,
			}
		)
		event.append(
			"custom_forms",
			{"form_doctype": "Sponsorship Enquiry", "route": form_route, "publish": 1},
		)
		event.insert(ignore_permissions=True)
		return event, form_route

	def make_tier(self, event_name, title):
		tier = frappe.new_doc("Sponsorship Tier")
		tier.update({"event": event_name, "title": title, "price": 100, "currency": "INR"})
		tier.insert(ignore_permissions=True)
		return tier.name

	def test_tier_options_filtered_to_form_event(self):
		event_a, route_a = self.make_sponsorship_event()
		event_b, _ = self.make_sponsorship_event()
		tier_a = self.make_tier(event_a.name, "Gold A")
		tier_b = self.make_tier(event_b.name, "Gold B")

		data = get_custom_form_data(event_a.route, route_a)
		tier_field = next(f for f in data["form_fields"] if f["fieldname"] == "tier")

		option_values = [option["value"] for option in tier_field["link_options"]]
		self.assertIn(tier_a, option_values)
		self.assertNotIn(tier_b, option_values, "tiers from other events must not leak")

	def test_link_field_without_event_is_not_filtered(self):
		# Country has no `event` field -> it must keep returning the full list.
		event_a, route_a = self.make_sponsorship_event()
		data = get_custom_form_data(event_a.route, route_a)
		country_field = next(f for f in data["form_fields"] if f["fieldname"] == "country")
		self.assertTrue(len(country_field["link_options"]) > 1)


class TestValidateExcludedFields(IntegrationTestCase):
	def test_hiding_mandatory_field_throws(self):
		# speakers is mandatory; it cannot be hidden.
		with self.assertRaises(frappe.ValidationError):
			validate_excluded_fields("Talk Proposal", "speakers")

	def test_unknown_field_throws(self):
		with self.assertRaises(frappe.ValidationError):
			validate_excluded_fields("Talk Proposal", "phone, not_a_field")

	def test_hiding_optional_field_passes(self):
		# phone is optional -> safe to hide.
		validate_excluded_fields("Talk Proposal", "phone")

	def test_system_field_is_noop(self):
		# Auto-set/system fields are never rendered; listing them is a harmless no-op.
		validate_excluded_fields("Talk Proposal", "event, submitted_by")

	def test_blank_is_noop(self):
		validate_excluded_fields("Talk Proposal", "")
		validate_excluded_fields("Talk Proposal", None)


class TestBuzzEventSaveValidatesExcludedFields(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Test Forms Category")
		cls.host = ensure_prompt_named_record("Event Host", "Test Forms Host")

	def make_event_doc(self, excluded_fields):
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
				"is_published": 1,
			}
		)
		event.set("custom_forms", [])
		event.append(
			"custom_forms",
			{
				"form_doctype": "Talk Proposal",
				"route": f"propose-{frappe.generate_hash(length=6)}",
				"publish": 1,
				"excluded_fields": excluded_fields,
			},
		)
		return event

	def test_save_hiding_mandatory_throws(self):
		event = self.make_event_doc("speakers")
		with self.assertRaises(frappe.ValidationError):
			event.insert(ignore_permissions=True)

	def test_save_with_unknown_field_throws(self):
		event = self.make_event_doc("phone, bogus_field")
		with self.assertRaises(frappe.ValidationError):
			event.insert(ignore_permissions=True)

	def test_save_hiding_optional_field_succeeds(self):
		event = self.make_event_doc("phone")
		event.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Buzz Event", event.name))
