from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.exceptions import NotPermitted
from buzz.api.imports import check_import, start_import
from buzz.api.imports.exceptions import EmptySpreadsheet, ImportNotReady, ImportsNotEnabled
from buzz.api.imports.services import DONE_EVENT, IMPORT_FLAG
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, EventTicketFactory, UserFactory


def published(message_event: str) -> list[dict]:
	return [call.args[1] for call in frappe.publish_realtime.call_args_list if call.args[0] == message_event]


class CheckInImportTest(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("import-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		cls.event = str(BuzzEventFactory.create(team=cls.team).name)
		cls.ticket = EventTicketFactory.create("submitted", event=cls.event, attendee_email="ada@example.com")
		cls.cancelled = EventTicketFactory.create("submitted", event=cls.event)
		cls.cancelled.cancel()

	def setUp(self):
		self.enterContext(self.set_user(self.owner))
		self.enterContext(patch("frappe.publish_realtime"))

	def check(self, text: str, **choices):
		return check_import(self.event, "checkins", text=text, choices=choices)

	def test_matches_columns_by_alias_and_offers_the_event_days(self):
		ticket = EventTicketFactory.create("submitted", event=self.event, attendee_email="alan@example.com")
		check = self.check(f"Ticket ID,Attendee Email\n{ticket.name},alan@example.com")

		self.assertEqual([column.field for column in check.columns], ["ticket", "email"])
		self.assertTrue(check.ready)
		self.assertEqual(check.ready_rows, 1)
		self.assertEqual(len(check.days), 1)

	def test_checks_in_by_email_and_leaves_repeats_out(self):
		start_import(self.event, "checkins", text="email\nada@example.com\nADA@example.com")

		self.assertEqual(frappe.db.count("Event Check In", {"ticket": self.ticket.name, "docstatus": 1}), 1)
		self.assertEqual(published(DONE_EVENT)[0]["imported"], 1)
		self.assertEqual(self.check("email\nada@example.com").ready_rows, 0)

	def test_a_cancelled_ticket_blocks_until_skipped(self):
		text = f"ticket\n{self.ticket.name}\n{self.cancelled.name}"

		rows = next(issue for issue in self.check(text).issues if issue.kind == "rows")
		self.assertEqual([row.row for row in rows.rows], [3])
		self.assertRaises(ImportNotReady, start_import, self.event, "checkins", text=text)
		self.assertTrue(self.check(text, skip_invalid=True).ready)

	def test_a_day_outside_the_event_is_a_row_error(self):
		check = self.check(f"ticket,date\n{self.ticket.name},{add_days(today(), 400)}")

		self.assertEqual(check.issues[0].kind, "rows")

	def test_an_unknown_column_waits_for_a_choice(self):
		text = f"ticket,notes\n{self.ticket.name},front door"

		issue = self.check(text).issues[0]
		self.assertEqual((issue.kind, issue.column, issue.choice), ("column", "notes", None))
		self.assertTrue(self.check(text, columns={"notes": ""}).ready)

	def test_a_file_needs_rows_under_its_header(self):
		self.assertRaises(EmptySpreadsheet, self.check, "ticket")

	def test_needs_the_team_flag(self):
		self.addCleanup(BuzzTeamFactory.set_settings, self.team, {IMPORT_FLAG: 1})
		BuzzTeamFactory.set_settings(self.team, {IMPORT_FLAG: 0})

		self.assertRaises(ImportsNotEnabled, self.check, "ticket\nx")

	def test_an_outsider_cannot_import(self):
		outsider = UserFactory.create_once("import-outsider@example.com").name
		with self.set_user(outsider):
			self.assertRaises(NotPermitted, self.check, "ticket\nx")

	def test_reads_cells_pasted_from_a_spreadsheet(self):
		check = self.check(f"Ticket ID\tNotes\n{self.ticket.name}\tok", columns={"Notes": ""})

		self.assertEqual(check.columns[0].field, "ticket")
		self.assertEqual(check.issues, [])
