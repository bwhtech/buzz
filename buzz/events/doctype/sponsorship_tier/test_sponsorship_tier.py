import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.test_permissions import add_member, create_event


class TestSponsorshipTier(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		suffix = frappe.generate_hash(length=6)
		self.owner = create_user(f"tier-owner-{suffix}@example.com", "Owner")
		self.team = create_owned_team(f"Tier Team {suffix}", self.owner)
		self.event = create_event(f"Tier Event {suffix}", self.team, is_published=1)
		self.suffix = suffix

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def member(self, team_role: str, team: str | None = None) -> str:
		user = create_user(f"{team_role.lower()}-{frappe.generate_hash(length=6)}@example.com", team_role)
		add_member(team or self.team, user, team_role)
		return user

	def new_tier(self, event: str | None = None) -> frappe.Document:
		return frappe.get_doc(
			{
				"doctype": "Sponsorship Tier",
				"event": event or self.event,
				"title": f"Gold {frappe.generate_hash(length=6)}",
				"price": 1000,
				"currency": "INR",
			}
		)

	def test_manager_can_insert_update_and_disable(self):
		frappe.set_user(self.member("Manager"))

		tier = self.new_tier().insert()
		tier.price = 2000
		tier.save()
		tier.enabled = 0
		tier.save()

		self.assertFalse(frappe.get_doc("Sponsorship Tier", tier.name).enabled)

	def test_member_of_another_team_is_refused(self):
		other_owner = create_user(f"other-owner-{self.suffix}@example.com", "Other")
		other_team = create_owned_team(f"Other Tier Team {self.suffix}", other_owner)

		frappe.set_user(self.member("Manager", other_team))
		with self.assertRaises(frappe.PermissionError):
			self.new_tier().insert()

	def test_viewer_is_refused(self):
		frappe.set_user(self.member("Viewer"))
		with self.assertRaises(frappe.PermissionError):
			self.new_tier().insert()

	def test_event_cannot_change_on_a_saved_tier(self):
		other_event = create_event(f"Other Event {self.suffix}", self.team, is_published=1)
		tier = self.new_tier().insert(ignore_permissions=True)

		tier.event = other_event
		with self.assertRaises(frappe.CannotChangeConstantError):
			tier.save(ignore_permissions=True)
