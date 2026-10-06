# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.tests import IntegrationTestCase

from buzz.api.tickets.windows import ADD_ON_CHANGE, CANCELLATION, TRANSFER
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import (
	FEATURE_FLAG_PREFIX,
	SEEDED_FIELDS,
	ZOOM_SEEDED_FIELD,
	feature_flags,
	get_team_settings,
	is_feature_enabled,
)
from buzz.tests.factories import BuzzTeamFactory, UserFactory

CUTOFF_FIELDS = (TRANSFER, ADD_ON_CHANGE, CANCELLATION)


def set_team_settings(team: str, **values):
	"""Write a team's settings the way a test reads them back."""
	frappe.db.set_value("Buzz Team Settings", team, values)


def create_webinar_template() -> str:
	name = "Settings Webinar Template"
	if not frappe.db.exists("Zoom Webinar Template", name):
		frappe.get_doc({"doctype": "Zoom Webinar Template", "id": name, "title": name, "type": 1}).insert(
			ignore_permissions=True
		)
	return name


def create_email_template(subject: str) -> str:
	name = f"Settings {subject}"
	if not frappe.db.exists("Email Template", name):
		frappe.get_doc(
			{"doctype": "Email Template", "name": name, "subject": subject, "response": subject}
		).insert(ignore_permissions=True)
	return name


class TestBuzzTeamSettings(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		# The rollback restores the Single but not its cached copy.
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")

	def set_globals(self, **values):
		for fieldname, value in values.items():
			frappe.db.set_single_value("Buzz Settings", fieldname, value)
		frappe.clear_document_cache("Buzz Settings", "Buzz Settings")

	def global_values(self) -> dict:
		template = create_email_template("Seeded")
		return {
			"support_email": "seeded-support@example.com",
			"allow_transfer_ticket_before_event_start_days": 3,
			"allow_add_ons_change_before_event_start_days": 4,
			"allow_ticket_cancellation_request_before_event_start_days": 5,
			"default_ticket_email_template": template,
			"default_booking_confirmation_email_template": template,
			"auto_send_pitch_deck": 1,
			"default_sponsor_deck_email_template": template,
			"default_sponsor_deck_reply_to": "seeded-sponsors@example.com",
			"default_sponsor_deck_cc": "seeded-cc@example.com",
		}

	def test_creating_a_team_seeds_its_settings_from_the_globals(self):
		values = self.global_values()
		self.set_globals(**values)
		owner = create_user("settings-seed@example.com", "Seed")

		team = create_owned_team("Settings Seed", owner)

		settings = get_team_settings(team)
		for fieldname, value in values.items():
			with self.subTest(fieldname=fieldname):
				self.assertEqual(settings.get(fieldname), value)

	def test_every_seeded_field_is_covered_by_the_seed_test(self):
		self.assertEqual(set(SEEDED_FIELDS), set(self.global_values()))

	def test_cutoffs_left_blank_fall_back_to_seven_days(self):
		# Int columns are NOT NULL, so the doctype default is the only place a fallback can live.
		self.set_globals(**dict.fromkeys(CUTOFF_FIELDS, None))
		owner = create_user("settings-blank@example.com", "Blank")

		team = create_owned_team("Settings Blank", owner)

		settings = get_team_settings(team)
		for fieldname in CUTOFF_FIELDS:
			with self.subTest(fieldname=fieldname):
				self.assertEqual(settings.get(fieldname), 7)

	def test_webinar_template_is_seeded_when_zoom_integration_is_installed(self):
		if "zoom_integration" not in frappe.get_installed_apps():
			self.skipTest("zoom_integration is not installed on this site")

		webinar_template = create_webinar_template()
		self.set_globals(default_webinar_template=webinar_template)
		owner = create_user("settings-zoom@example.com", "Zoom")

		team = create_owned_team("Settings Zoom", owner)

		# Without this the assertion below passes vacuously on None == None.
		self.assertTrue(frappe.get_meta("Buzz Team Settings").has_field(ZOOM_SEEDED_FIELD))
		self.assertEqual(get_team_settings(team).get(ZOOM_SEEDED_FIELD), webinar_template)

	def test_patch_seeds_teams_that_predate_the_doctype_and_is_idempotent(self):
		from buzz.patches.create_team_settings_for_existing_teams import execute

		values = self.global_values()
		self.set_globals(**values)
		owner = create_user("settings-legacy@example.com", "Legacy")
		team = create_owned_team("Settings Legacy", owner)
		frappe.delete_doc("Buzz Team Settings", team, force=True, ignore_permissions=True)

		execute()
		execute()

		settings = get_team_settings(team)
		self.assertEqual(settings.support_email, values["support_email"])

	def test_seeding_skips_the_webinar_template_without_zoom_integration(self):
		owner = create_user("settings-no-zoom@example.com", "NoZoom")

		with patch("frappe.get_installed_apps", return_value=["frappe", "buzz"]):
			team = create_owned_team("Settings No Zoom", owner)

		self.assertIsNone(get_team_settings(team).get(ZOOM_SEEDED_FIELD))


class TestTeamTaxDetails(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		owner = create_user("team-tax-owner@example.com", "Owner")
		self.settings = frappe.get_doc("Buzz Team Settings", create_owned_team("Team Tax Team", owner))

	def save_tax_details(self, **values):
		self.settings.update(values)
		self.settings.save()

	def test_refuses_a_tax_id_without_the_rest(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_tax_details(tax_id="22AAAAA0000A1Z5")

	def test_refuses_a_legal_name_without_a_tax_id(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_tax_details(legal_name="Acme Events", billing_address="12 MG Road")

	def test_saves_complete_details_with_an_uppercase_tax_id(self):
		self.save_tax_details(
			legal_name="Acme Events", tax_id=" 22aaaaa0000a1z5 ", billing_address="12 MG Road"
		)
		self.assertEqual(self.settings.tax_id, "22AAAAA0000A1Z5")

	def test_empty_details_are_allowed(self):
		self.save_tax_details(legal_name="", tax_id="", billing_address="")
		self.assertIsNone(self.settings.tax_id)

	def test_refuses_removing_the_tax_id(self):
		self.save_tax_details(
			legal_name="Acme Events", tax_id="22AAAAA0000A1Z5", billing_address="12 MG Road"
		)
		with self.assertRaises(frappe.ValidationError):
			self.save_tax_details(legal_name="", tax_id="", billing_address="")

	def test_changing_the_tax_id_is_allowed(self):
		self.save_tax_details(
			legal_name="Acme Events", tax_id="22AAAAA0000A1Z5", billing_address="12 MG Road"
		)
		self.save_tax_details(tax_id="29BBBBB1111B1Z5")
		self.assertEqual(self.settings.tax_id, "29BBBBB1111B1Z5")


TEST_FLAG = "feature_test_flag"


class TestFeatureFlags(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_custom_field(
			"Buzz Team Settings",
			{"fieldname": TEST_FLAG, "label": "Test Flag", "fieldtype": "Check", "permlevel": 1},
		)

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		frappe.delete_doc("Custom Field", f"Buzz Team Settings-{TEST_FLAG}", force=True)
		frappe.db.sql_ddl(f"alter table `tabBuzz Team Settings` drop column `{TEST_FLAG}`")

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.owner = UserFactory.create_once("feature-flag-owner@example.com").name
		self.team = BuzzTeamFactory.create_owned_by(self.owner).name
		self.addCleanup(frappe.clear_document_cache, "Buzz Team Settings", self.team)

	def save_flag(self, value: int):
		settings = frappe.get_doc("Buzz Team Settings", self.team)
		settings.set(TEST_FLAG, value)
		settings.save()

	def test_flag_is_off_until_saved_on(self):
		self.assertFalse(is_feature_enabled(self.team, TEST_FLAG))
		self.save_flag(1)
		self.assertTrue(is_feature_enabled(self.team, TEST_FLAG))
		self.assertEqual(feature_flags(self.team)[TEST_FLAG], True)

	def test_unknown_flag_throws(self):
		with self.assertRaises(frappe.ValidationError):
			is_feature_enabled(self.team, "feature_does_not_exist")

	def test_team_owner_cannot_turn_a_flag_on(self):
		frappe.set_user(self.owner)
		self.save_flag(1)
		self.assertFalse(is_feature_enabled(self.team, TEST_FLAG))

	def test_every_flag_is_a_restricted_check_field(self):
		for field in frappe.get_meta("Buzz Team Settings").fields:
			if field.fieldname.startswith(FEATURE_FLAG_PREFIX):
				self.assertEqual(field.fieldtype, "Check", field.fieldname)
				self.assertGreaterEqual(field.permlevel, 1, field.fieldname)
