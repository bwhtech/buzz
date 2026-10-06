import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events import get_event_ticket_types, update_tax_settings, update_team_tax_details
from buzz.api.events.exceptions import CannotManageEvent, TaxDetailsMissing
from buzz.api.teams.exceptions import CannotEditTeam
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory

TAX_DETAILS = {
	"legal_name": "Acme Events Pvt Ltd",
	"tax_id": "29abcde1234f1z5",
	"billing_address": "12 MG Road, Bengaluru",
}


class TaxesTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("taxes-owner@example.com").name
		cls.manager = UserFactory.create_once("taxes-manager@example.com").name
		cls.viewer = UserFactory.create_once("taxes-viewer@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.manager, team_role="Manager")
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.viewer, team_role="Viewer")

	def setUp(self):
		self.event = str(BuzzEventFactory.create(team=self.team).name)
		BuzzTeamFactory.set_settings(self.team, dict.fromkeys(TAX_DETAILS))

	def test_refuses_tax_until_the_team_has_tax_details(self):
		with self.set_user(self.owner), self.assertRaises(TaxDetailsMissing):
			self.turn_tax_on()

	def test_charges_tax_once_the_team_has_tax_details(self):
		with self.set_user(self.owner):
			update_team_tax_details(self.event, **TAX_DETAILS)
			self.turn_tax_on()

		event = frappe.get_doc("Buzz Event", self.event)
		self.assertEqual((event.apply_tax, event.tax_inclusive, event.tax_percentage), (1, 1, 12))

	def test_turns_tax_off_without_tax_details(self):
		event = str(BuzzEventFactory.create("with_tax", team=self.team).name)

		with self.set_user(self.owner):
			update_tax_settings(event, False, False, "GST", 18)

		self.assertEqual(frappe.db.get_value("Buzz Event", event, "apply_tax"), 0)

	def test_viewer_cannot_change_tax_settings(self):
		with self.set_user(self.viewer), self.assertRaises(CannotManageEvent):
			update_tax_settings(self.event, False, False, "GST", 18)

	def test_saves_team_tax_details(self):
		with self.set_user(self.owner):
			update_team_tax_details(self.event, **TAX_DETAILS)

		saved = frappe.db.get_value("Buzz Team Settings", self.team, list(TAX_DETAILS), as_dict=True)
		self.assertEqual(saved.tax_id, "29ABCDE1234F1Z5")
		self.assertEqual(saved.legal_name, TAX_DETAILS["legal_name"])

	def test_refuses_incomplete_team_tax_details(self):
		with self.set_user(self.owner), self.assertRaises(frappe.ValidationError):
			update_team_tax_details(self.event, **{**TAX_DETAILS, "billing_address": "  "})

	def test_refuses_empty_team_tax_details(self):
		with self.set_user(self.owner), self.assertRaises(frappe.ValidationError):
			update_team_tax_details(self.event, legal_name="", tax_id=" ", billing_address="")

	def test_only_team_admins_add_tax_details(self):
		with self.set_user(self.manager), self.assertRaises(CannotEditTeam):
			update_team_tax_details(self.event, **TAX_DETAILS)

	def test_payload_says_whether_the_team_has_tax_details(self):
		with self.set_user(self.owner):
			self.assertIsNone(get_event_ticket_types(self.event).team_tax_id)
			update_team_tax_details(self.event, **TAX_DETAILS)
			registration = get_event_ticket_types(self.event)

		self.assertEqual(registration.team_tax_id, "29ABCDE1234F1Z5")
		self.assertEqual(registration.team_legal_name, TAX_DETAILS["legal_name"])
		self.assertTrue(registration.can_edit_team)

	def turn_tax_on(self):
		update_tax_settings(self.event, True, True, "GST", 12)
