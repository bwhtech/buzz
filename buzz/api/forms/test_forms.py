import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from buzz.api.forms import get_dial_codes
from buzz.api.forms.exceptions import MandatoryFieldsHidden, UnknownExcludedFields
from buzz.api.forms.fields import (
	STANDARD_EXCLUDE_FIELDS,
	get_form_fields,
	get_link_field_options,
	parse_excluded_fields,
	validate_excluded_fields,
)
from buzz.tests.factories import EventCategoryFactory, EventHostFactory, SponsorshipTierFactory

# Renderable Talk Proposal fields (after STANDARD_EXCLUDE_FIELDS + auto-set event/submitted_by):
#   title (reqd, Data), description (Text Editor), speakers (reqd, Table), phone (Phone)
TALK_PROPOSAL_EXCLUDE = STANDARD_EXCLUDE_FIELDS | {"event", "submitted_by"}
LAYOUT_BREAKS = ("Section Break", "Column Break")


def ensure_prompt_named_record(doctype, name):
	# Event Category uses autoname "prompt" -> name set explicitly.
	if frappe.db.exists(doctype, name):
		return name
	doc = frappe.new_doc(doctype)
	doc.name = name
	doc.insert(ignore_permissions=True)
	return doc.name


def ensure_event_host(host_name):
	# Event Host autonames to a hash, so `host_name` is both the label and the lookup key.
	existing = frappe.db.get_value("Event Host", {"host_name": host_name}, "name")
	if existing:
		return existing
	doc = frappe.new_doc("Event Host")
	doc.host_name = host_name
	doc.insert(ignore_permissions=True)
	return doc.name


class TestParseExcludedFields(UnitTestCase):
	def test_blank_returns_none(self):
		for blank in (None, "", "   ", ", ,,"):
			with self.subTest(blank=blank):
				self.assertIsNone(parse_excluded_fields(blank))

	def test_trims_and_drops_empties(self):
		self.assertEqual(parse_excluded_fields("a, b ,,c"), {"a", "b", "c"})

	def test_single_field(self):
		self.assertEqual(parse_excluded_fields("title"), {"title"})


class TestGetFormFields(IntegrationTestCase):
	def test_excluding_a_field_drops_it(self):
		returned = self.fieldnames(get_form_fields("Talk Proposal", TALK_PROPOSAL_EXCLUDE | {"phone"}))

		self.assertNotIn("phone", returned)
		self.assertTrue({"title", "description", "speakers"} <= returned)

	def test_no_extra_exclude_returns_all_renderable(self):
		returned = self.fieldnames(get_form_fields("Talk Proposal", TALK_PROPOSAL_EXCLUDE))

		self.assertTrue({"title", "description", "speakers", "phone"} <= returned)

	def test_layout_breaks_pass_through(self):
		# With layout breaks on, section/column breaks are emitted even when other fields are excluded.
		exclude_fields = TALK_PROPOSAL_EXCLUDE | {"description", "speakers", "phone"}
		fields = get_form_fields("Talk Proposal", exclude_fields, with_layout_breaks=True)

		real_fields = self.fieldnames(f for f in fields if f["fieldtype"] not in LAYOUT_BREAKS)
		self.assertIn("title", real_fields)
		self.assertFalse({"description", "speakers", "phone"} & real_fields)
		self.assertTrue([f for f in fields if f["fieldtype"] in LAYOUT_BREAKS])

	def test_table_field_carries_child_fields(self):
		fields = get_form_fields("Talk Proposal", TALK_PROPOSAL_EXCLUDE)
		speakers = next(f for f in fields if f["fieldname"] == "speakers")

		self.assertTrue({"first_name", "email"} <= self.fieldnames(speakers["child_fields"]))

	def fieldnames(self, fields) -> set[str]:
		return {f["fieldname"] for f in fields}


class TestGetLinkFieldOptions(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = EventCategoryFactory.create().name
		EventHostFactory.create()

	def test_options_have_value_label_shape(self):
		options = get_link_field_options("Event Host")

		self.assertTrue(options)
		self.assertTrue(all(set(option) == {"value", "label"} for option in options))

	def test_no_title_field_label_falls_back_to_name(self):
		# Event Category has no title field -> label mirrors the name.
		self.assertEqual(self.label_of("Event Category", self.category), self.category)

	def test_title_field_used_as_label(self):
		# Sponsorship Tier names are hashes; its title field is the readable label.
		tier = SponsorshipTierFactory.create(title="Gold Tier").name

		self.assertEqual(self.label_of("Sponsorship Tier", tier), "Gold Tier")
		self.assertNotEqual(tier, "Gold Tier")

	def test_null_title_falls_back_to_name(self):
		tier = SponsorshipTierFactory.create().name
		# Blank the title directly (bypasses the reqd validation) to exercise the fallback.
		frappe.db.set_value("Sponsorship Tier", tier, "title", "")

		self.assertEqual(self.label_of("Sponsorship Tier", tier), tier)

	def label_of(self, doctype: str, name: str) -> str:
		return next(o["label"] for o in get_link_field_options(doctype) if o["value"] == name)


class TestValidateExcludedFields(IntegrationTestCase):
	def setUp(self):
		frappe.clear_messages()

	def test_hiding_mandatory_field_throws(self):
		# speakers is mandatory; it cannot be hidden.
		with self.assertRaises(MandatoryFieldsHidden):
			validate_excluded_fields("Talk Proposal", "speakers")

		self.assertIn("speakers", frappe.local.message_log[-1]["message"])

	def test_unknown_field_throws(self):
		with self.assertRaises(UnknownExcludedFields):
			validate_excluded_fields("Talk Proposal", "phone, not_a_field")

		self.assertIn("not_a_field", frappe.local.message_log[-1]["message"])

	def test_hiding_optional_field_passes(self):
		# phone is optional -> safe to hide.
		validate_excluded_fields("Talk Proposal", "phone")

	def test_system_field_is_noop(self):
		# Auto-set/system fields are never rendered; listing them is a harmless no-op.
		validate_excluded_fields("Talk Proposal", "event, submitted_by")

	def test_blank_is_noop(self):
		validate_excluded_fields("Talk Proposal", "")
		validate_excluded_fields("Talk Proposal", None)


class TestDialCodes(IntegrationTestCase):
	def test_shape_and_uniqueness(self):
		codes = get_dial_codes()
		self.assertTrue(codes)
		self.assertTrue(all(set(entry) == {"country", "code", "dial_code"} for entry in codes))
		dial_codes = [entry["dial_code"] for entry in codes]
		self.assertEqual(len(dial_codes), len(set(dial_codes)), "dial codes must be de-duplicated")
		self.assertIn("+91", dial_codes)
