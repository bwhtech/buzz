# Copyright (c) 2026, BWH Studios and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.tickets.windows import ADD_ON_CHANGE, CANCELLATION, TRANSFER
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import (
	SEEDED_FIELDS,
	ZOOM_SEEDED_FIELD,
	get_team_settings,
)

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
