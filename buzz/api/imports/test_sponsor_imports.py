from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.exceptions import NotPermitted
from buzz.api.imports import check_import, get_import_status, start_import
from buzz.api.imports.exceptions import (
	EmptySpreadsheet,
	ImportNotReady,
	ImportRunning,
	ImportsNotEnabled,
	UnreadableFile,
)
from buzz.api.imports.services import save_status, status_key
from buzz.events.doctype.buzz_team_settings.buzz_team_settings import IMPORT_FLAG
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	FileFactory,
	SponsorshipTierFactory,
	UserFactory,
)


class SponsorImportTest(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("import-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		cls.event = str(BuzzEventFactory.create(team=cls.team).name)
		cls.tier = SponsorshipTierFactory.create(event=cls.event, title="Gold")

	def setUp(self):
		self.enterContext(self.set_user(self.owner))

	def check(self, text: str, **choices):
		return check_import(self.event, text=text, choices=choices)

	def done(self):
		return get_import_status(self.event)

	def test_matches_columns_by_alias_and_previews_the_tier_title(self):
		check = self.check("Sponsor,Package,Country\nAcme,gold,India")

		self.assertEqual([column.field for column in check.columns], ["company_name", "tier", "country"])
		self.assertTrue(check.ready)
		self.assertEqual(check.preview[0].values["tier"], "Gold")
		self.assertIn("Without a logo, so they show their name until one is added: 1.", check.notes)

	def test_imports_a_sponsor_and_leaves_repeats_out(self):
		start_import(self.event, text="Company,Tier,Website\nGlobex,Gold,globex.test\nglobex,Gold,")

		sponsor = frappe.get_doc("Event Sponsor", {"event": self.event, "company_name": "Globex"})
		self.assertEqual((sponsor.tier, sponsor.company_logo), (self.tier.name, None))
		self.assertEqual(sponsor.website, "https://globex.test")
		self.assertEqual((self.done().state, self.done().imported), ("done", 1))
		self.assertEqual(self.check("Company,Tier\nGlobex,Gold").ready_rows, 0)

	def test_a_bad_row_is_named_and_blocks_until_skipped(self):
		text = "Company,Tier,Email\nInitech,Gold,ok@initech.test\nHooli,Gold,not-an-email"

		rows = next(issue for issue in self.check(text).issues if issue.kind == "rows")
		self.assertEqual([(row.row, row.title) for row in rows.rows], [(3, "Hooli")])
		self.assertRaises(ImportNotReady, start_import, self.event, text=text)
		self.assertTrue(self.check(text, skip_invalid=True).ready)

	def test_a_row_number_counts_blank_rows_above_it(self):
		rows = self.check("Company,Tier,Email\n\nHooli,Gold,not-an-email").issues[0].rows

		self.assertEqual(rows[0].row, 3)

	def test_a_file_without_a_company_column_asks_for_one(self):
		issue = self.check("Tier\nGold").issues[0]

		self.assertEqual((issue.kind, issue.label), ("missing", "Company Name"))

	def test_a_second_import_waits_for_the_running_one(self):
		self.addCleanup(frappe.cache.delete_value, status_key(self.event))
		save_status(self.event, state="running", done=1, total=10)

		self.assertRaises(ImportRunning, start_import, self.event, text="Company,Tier\nVandelay,Gold")

	def test_a_broken_excel_file_is_unreadable(self):
		file = FileFactory.create(file_name="sponsors.xlsx", content=b"not a workbook", is_private=1)

		self.assertRaises(UnreadableFile, check_import, self.event, file_url=file.file_url)

	def test_a_name_longer_than_the_field_is_a_row_error(self):
		rows = self.check(f"Company,Tier\n{'A' * 141},Gold").issues[0].rows

		self.assertEqual(rows[0].reason, "Company Name is longer than 140 characters.")

	def test_an_unknown_tier_cannot_be_left_empty(self):
		issue = self.check("Company,Tier\nAcme,Diamond").issues[0]

		self.assertEqual((issue.kind, issue.value), ("value", "Diamond"))
		self.assertNotIn("__blank__", [option.value for option in issue.options])

	def test_a_row_that_fails_is_reported_with_its_reason(self):
		with patch(
			"buzz.api.imports.sponsors.SponsorImporter.import_record",
			side_effect=frappe.ValidationError("Nope"),
		):
			start_import(self.event, text="Company,Tier\nUmbrella,Gold")

		self.assertEqual(
			[row.model_dump() for row in self.done().failed],
			[{"row": 2, "title": "Umbrella", "reason": "Nope"}],
		)
		self.assertEqual(self.done().failed_cells, [["Umbrella", "Gold"]])

	def test_an_unknown_column_waits_for_a_choice(self):
		text = "Company,Tier,Booth\nAcme,Gold,A1"

		issue = self.check(text).issues[0]
		self.assertEqual((issue.kind, issue.column, issue.choice), ("column", "Booth", None))
		self.assertTrue(self.check(text, columns={"Booth": ""}).ready)

	def test_reads_cells_pasted_from_a_spreadsheet(self):
		check = self.check("Company\tTier\tBooth\nAcme\tGold\tA1", columns={"Booth": ""})

		self.assertEqual(check.columns[0].field, "company_name")
		self.assertEqual(check.issues, [])

	def test_a_file_needs_rows_under_its_header(self):
		self.assertRaises(EmptySpreadsheet, self.check, "Company,Tier")

	def test_needs_the_team_flag(self):
		self.addCleanup(BuzzTeamFactory.set_settings, self.team, {IMPORT_FLAG: 1})
		BuzzTeamFactory.set_settings(self.team, {IMPORT_FLAG: 0})

		self.assertRaises(ImportsNotEnabled, self.check, "Company,Tier\nAcme,Gold")

	def test_an_outsider_cannot_import(self):
		outsider = UserFactory.create_once("import-outsider@example.com").name
		with self.set_user(outsider):
			self.assertRaises(NotPermitted, self.check, "Company,Tier\nAcme,Gold")
