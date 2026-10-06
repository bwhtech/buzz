import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.forms import get_event_proposal_form_data, submit_event_proposal
from buzz.api.forms.exceptions import LoginRequired, ProposalsNotAccepted
from buzz.tests.factories import EventCategoryFactory

OPEN_TO_GUESTS = {"accept_event_proposals": 1, "allow_guest_event_proposals": 1}


class TestEventProposalForm(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = EventCategoryFactory.create().name

	def setUp(self):
		frappe.clear_messages()
		# The rollback restores the settings row but not its cached copy.
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")
		self.enterContext(self.change_settings("Buzz Settings", OPEN_TO_GUESTS))

	def test_form_data_carries_the_banner_and_success_copy(self):
		with self.change_settings(
			"Buzz Settings", event_proposal_banner_title="Pitch us", event_proposal_success_title="Got it"
		):
			data = get_event_proposal_form_data()

		self.assertEqual((data.banner_title, data.success_title), ("Pitch us", "Got it"))
		self.assertTrue(data.form_fields)
		self.assertNotIn("status", {f["fieldname"] for f in data.form_fields})

	def test_disabled_proposals_are_not_found(self):
		with self.change_settings("Buzz Settings", accept_event_proposals=0):
			with self.assertRaises(ProposalsNotAccepted):
				get_event_proposal_form_data()

		self.assertIn("not being accepted", frappe.local.message_log[-1]["message"])

	def test_guest_blocked_when_guest_proposals_are_off(self):
		with self.change_settings("Buzz Settings", allow_guest_event_proposals=0):
			with self.set_user("Guest"), self.assertRaises(LoginRequired):
				get_event_proposal_form_data()

	def test_submit_drops_fields_outside_the_form(self):
		payload = self.proposal_payload(status="Approved")

		submit_event_proposal(data=payload)

		created = self.submitted_proposal(payload["title"])
		# status is excluded, so a posted value must not stick.
		self.assertNotEqual(created.status, "Approved")
		self.assertEqual(created.about, payload["about"])

	def test_guest_can_submit(self):
		payload = self.proposal_payload()

		with self.set_user("Guest"):
			submit_event_proposal(data=payload)

		# Event Proposal has no submitted_by field, so the proposer is only the doc owner.
		self.assertEqual(self.submitted_proposal(payload["title"]).owner, "Guest")

	def test_submit_blocked_when_proposals_are_closed(self):
		with self.change_settings("Buzz Settings", accept_event_proposals=0):
			with self.assertRaises(ProposalsNotAccepted):
				submit_event_proposal(data=self.proposal_payload())

	def proposal_payload(self, **overrides):
		return {
			"title": f"Proposal {frappe.generate_hash(length=6)}",
			"category": self.category,
			"start_date": add_days(today(), 30),
			"start_time": "10:00:00",
			"end_time": "18:00:00",
			"about": "A proposal raised by the forms test suite.",
			**overrides,
		}

	def submitted_proposal(self, title: str):
		return frappe.get_last_doc("Event Proposal", filters={"title": title})
