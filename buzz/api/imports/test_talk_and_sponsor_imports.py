from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.imports import check_import, start_import
from buzz.api.imports.services import CREATE, DONE_EVENT
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, SponsorshipTierFactory, UserFactory


class ImportTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("talk-import-owner@example.com").name
		team = BuzzTeamFactory.create_owned_by(cls.owner).name
		cls.event = str(BuzzEventFactory.create(team=team).name)

	def setUp(self):
		self.enterContext(self.set_user(self.owner))
		self.realtime = self.enterContext(patch("frappe.publish_realtime"))

	def done(self) -> dict:
		return next(call.args[1] for call in self.realtime.call_args_list if call.args[0] == DONE_EVENT)


class TalkImportTest(ImportTestCase):
	def test_makes_accepted_talks_with_new_speakers_and_no_welcome_email(self):
		day = add_days(today(), 30)
		text = (
			"Talk Title,Speaker Email,Speaker Name,Organisation,Room,Day,Slot,Ends\n"
			f"Async all the way down,priya@import.test,Priya Raman,Razorpay,Main Hall,{day},10:30,11:00\n"
		)
		choices = {"values": {"track": {"Main Hall": CREATE}}}

		check = check_import(self.event, "talks", text=text, choices=choices)
		self.assertTrue(check.ready)
		self.assertIn("Speakers new to Buzz, who get a profile: 1.", check.notes)

		start_import(self.event, "talks", text=text, choices=choices)

		proposal = frappe.get_doc("Talk Proposal", {"event": self.event, "title": "Async all the way down"})
		self.assertEqual(proposal.status, "Accepted")
		self.assertEqual(frappe.db.get_value("User", "priya@import.test", "send_welcome_email"), 0)
		profile = frappe.get_doc("Speaker Profile", {"user": "priya@import.test"})
		self.assertEqual(profile.company, "Razorpay")
		schedule = frappe.get_doc("Buzz Event", self.event).schedule
		self.assertEqual([(row.track, str(row.start_time)) for row in schedule], [("Main Hall", "10:30:00")])

	def test_an_unknown_track_waits_for_a_choice(self):
		day = add_days(today(), 30)
		text = f"title,speaker email,track,date,start,end\nTyping the untypable,sana@import.test,Lobby,{day},10:00,11:00"

		issue = check_import(self.event, "talks", text=text).issues[0]

		self.assertEqual((issue.kind, issue.value, issue.choice), ("value", "Lobby", None))

	def test_a_row_that_fails_is_reported_with_its_reason(self):
		text = "title,speaker email\nPackaging in 2026,vik@import.test"
		with patch(
			"buzz.api.imports.talks.TalkImporter.import_record", side_effect=frappe.ValidationError("Nope")
		):
			start_import(self.event, "talks", text=text)

		self.assertEqual(self.done()["failed"], [{"row": 2, "reason": "Nope"}])
		self.assertEqual(self.done()["failed_cells"], [["Packaging in 2026", "vik@import.test"]])


class SponsorImportTest(ImportTestCase):
	def test_maps_tiers_by_title_and_takes_a_sponsor_without_a_logo(self):
		tier = SponsorshipTierFactory.create(event=self.event, title="Gold")
		text = "Company,Tier,Country\nAcme,gold,India"

		check = check_import(self.event, "sponsors", text=text)
		self.assertTrue(check.ready)
		self.assertIn("Without a logo, so they show their name until one is added: 1.", check.notes)

		start_import(self.event, "sponsors", text=text)

		sponsor = frappe.get_doc("Event Sponsor", {"event": self.event, "company_name": "Acme"})
		self.assertEqual((sponsor.tier, sponsor.country, sponsor.company_logo), (tier.name, "India", None))
		self.assertEqual(check_import(self.event, "sponsors", text=text).ready_rows, 0)

	def test_an_unknown_tier_cannot_be_created_or_left_empty(self):
		issue = check_import(self.event, "sponsors", text="Company,Tier\nAcme,Diamond").issues[0]

		self.assertEqual((issue.kind, issue.value), ("value", "Diamond"))
		self.assertNotIn(CREATE, [option.value for option in issue.options])
		self.assertNotIn("__blank__", [option.value for option in issue.options])
