import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events import get_event_ticket_types, update_tax_settings, update_team_tax_details
from buzz.api.events.exceptions import CannotManageEvent, TaxDetailsMissing
from buzz.api.events.test_events import create_event
from buzz.api.teams.exceptions import CannotEditTeam
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.test_permissions import add_member

TAX_DETAILS = {
	"legal_name": "Acme Events Pvt Ltd",
	"tax_id": "29abcde1234f1z5",
	"billing_address": "12 MG Road, Bengaluru",
}


class TaxesTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.owner = create_user("taxes-owner@example.com", "Owner")
		cls.manager = create_user("taxes-manager@example.com", "Manager")
		cls.viewer = create_user("taxes-viewer@example.com", "Viewer")
		cls.team = create_owned_team("Taxes Team", cls.owner)
		add_member(cls.team, cls.manager, "Manager")
		add_member(cls.team, cls.viewer, "Viewer")

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.event = create_event("Taxes Event", self.team)
		frappe.db.set_value("Buzz Team Settings", self.team, dict.fromkeys(TAX_DETAILS))
		frappe.clear_document_cache("Buzz Team Settings", self.team)

	def turn_tax_on(self):
		update_tax_settings(self.event, True, True, "GST", 12)

	def test_refuses_tax_until_the_team_has_tax_details(self):
		frappe.set_user(self.owner)
		with self.assertRaises(TaxDetailsMissing):
			self.turn_tax_on()

	def test_charges_tax_once_the_team_has_tax_details(self):
		frappe.set_user(self.owner)
		update_team_tax_details(self.event, **TAX_DETAILS)

		self.turn_tax_on()

		event = frappe.get_doc("Buzz Event", self.event)
		self.assertEqual((event.apply_tax, event.tax_inclusive, event.tax_percentage), (1, 1, 12))

	def test_turns_tax_off_without_tax_details(self):
		frappe.db.set_value("Buzz Event", self.event, "apply_tax", 1)
		frappe.set_user(self.owner)

		update_tax_settings(self.event, False, False, "GST", 18)

		self.assertEqual(frappe.db.get_value("Buzz Event", self.event, "apply_tax"), 0)

	def test_viewer_cannot_change_tax_settings(self):
		frappe.set_user(self.viewer)
		with self.assertRaises(CannotManageEvent):
			update_tax_settings(self.event, False, False, "GST", 18)

	def test_saves_team_tax_details(self):
		frappe.set_user(self.owner)
		update_team_tax_details(self.event, **TAX_DETAILS)

		saved = frappe.db.get_value("Buzz Team Settings", self.team, list(TAX_DETAILS), as_dict=True)
		self.assertEqual(saved.tax_id, "29ABCDE1234F1Z5")
		self.assertEqual(saved.legal_name, TAX_DETAILS["legal_name"])

	def test_refuses_incomplete_team_tax_details(self):
		frappe.set_user(self.owner)
		with self.assertRaises(frappe.ValidationError):
			update_team_tax_details(self.event, **{**TAX_DETAILS, "billing_address": "  "})

	def test_refuses_empty_team_tax_details(self):
		frappe.set_user(self.owner)
		with self.assertRaises(frappe.ValidationError):
			update_team_tax_details(self.event, legal_name="", tax_id=" ", billing_address="")

	def test_only_team_admins_add_tax_details(self):
		frappe.set_user(self.manager)
		with self.assertRaises(CannotEditTeam):
			update_team_tax_details(self.event, **TAX_DETAILS)

	def test_payload_says_whether_the_team_has_tax_details(self):
		frappe.set_user(self.owner)
		self.assertFalse(get_event_ticket_types(self.event).team_has_tax_details)

		update_team_tax_details(self.event, **TAX_DETAILS)

		registration = get_event_ticket_types(self.event)
		self.assertTrue(registration.team_has_tax_details)
		self.assertTrue(registration.can_edit_team)
