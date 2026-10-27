import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.forms import get_dial_codes
from buzz.api.forms.fields import (
	STANDARD_EXCLUDE_FIELDS,
	get_form_fields,
	get_link_field_options,
)
from buzz.tests.factories import EventCategoryFactory, EventHostFactory, SponsorshipTierFactory

# Leaves title and speakers (both mandatory), description and phone renderable.
TALK_PROPOSAL_EXCLUDE = STANDARD_EXCLUDE_FIELDS | {"event", "submitted_by"}
LAYOUT_BREAKS = ("Section Break", "Column Break")


class TestGetFormFields(IntegrationTestCase):
	def test_excluding_a_field_drops_it(self):
		returned = self.fieldnames(get_form_fields("Talk Proposal", TALK_PROPOSAL_EXCLUDE | {"phone"}))

		self.assertNotIn("phone", returned)
		self.assertTrue({"title", "description", "speakers"} <= returned)

	def test_no_extra_exclude_returns_all_renderable(self):
		returned = self.fieldnames(get_form_fields("Talk Proposal", TALK_PROPOSAL_EXCLUDE))

		self.assertTrue({"title", "description", "speakers", "phone"} <= returned)

	def test_layout_breaks_pass_through(self):
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
		# Event Category has no title field.
		self.assertEqual(self.label_of("Event Category", self.category), self.category)

	def test_title_field_used_as_label(self):
		# Sponsorship Tier names are hashes; its title field is the readable label.
		tier = SponsorshipTierFactory.create(title="Gold Tier").name

		self.assertEqual(self.label_of("Sponsorship Tier", tier), "Gold Tier")
		self.assertNotEqual(tier, "Gold Tier")

	def test_null_title_falls_back_to_name(self):
		tier = SponsorshipTierFactory.create().name
		# set_value skips the mandatory check on title.
		frappe.db.set_value("Sponsorship Tier", tier, "title", "")

		self.assertEqual(self.label_of("Sponsorship Tier", tier), tier)

	def label_of(self, doctype: str, name: str) -> str:
		return next(o["label"] for o in get_link_field_options(doctype) if o["value"] == name)


class TestDialCodes(IntegrationTestCase):
	def test_shape_and_uniqueness(self):
		codes = get_dial_codes()
		self.assertTrue(codes)
		self.assertTrue(all(set(entry) == {"country", "code", "dial_code"} for entry in codes))
		dial_codes = [entry["dial_code"] for entry in codes]
		self.assertEqual(len(dial_codes), len(set(dial_codes)), "dial codes must be de-duplicated")
		self.assertIn("+91", dial_codes)
