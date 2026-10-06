import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	SponsorshipTierFactory,
	UserFactory,
)


class TestSponsorshipTier(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		owner = UserFactory.create_once("tier-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(owner).name
		cls.event = BuzzEventFactory.create(team=cls.team).name
		cls.manager = cls.add_member("tier-manager@example.com", cls.team, "Manager")
		cls.viewer = cls.add_member("tier-viewer@example.com", cls.team, "Viewer")
		other_team = BuzzTeamFactory.create_owned_by().name
		cls.other_team_manager = cls.add_member("tier-other-manager@example.com", other_team, "Manager")

	def test_manager_can_insert_update_and_disable(self):
		with self.set_user(self.manager):
			tier = SponsorshipTierFactory.create(event=self.event)
			tier.prices[0].price = 2000
			tier.save()
			tier.enabled = 0
			tier.save()

		self.assertEqual(frappe.db.get_value("Sponsorship Tier", tier.name, "enabled"), 0)

	def test_member_of_another_team_is_refused(self):
		with self.set_user(self.other_team_manager), self.assertRaises(frappe.PermissionError):
			SponsorshipTierFactory.create(event=self.event)

	def test_viewer_is_refused(self):
		with self.set_user(self.viewer), self.assertRaises(frappe.PermissionError):
			SponsorshipTierFactory.create(event=self.event)

	def test_event_cannot_change_on_a_saved_tier(self):
		tier = SponsorshipTierFactory.create(event=self.event)

		tier.event = BuzzEventFactory.create(team=self.team).name
		with self.assertRaises(frappe.CannotChangeConstantError):
			tier.save()

	def test_tier_needs_at_least_one_price(self):
		with self.assertRaises(frappe.ValidationError):
			SponsorshipTierFactory.create(event=self.event, prices=[])

	def test_currency_cannot_repeat(self):
		prices = [{"currency": "INR", "price": 1000}, {"currency": "INR", "price": 500}]
		with self.assertRaises(frappe.ValidationError):
			SponsorshipTierFactory.create(event=self.event, prices=prices)

	@classmethod
	def add_member(cls, email: str, team: str, team_role: str) -> str:
		user = UserFactory.create_once(email).name
		BuzzTeamMembershipFactory.create(team=team, user=user, team_role=team_role)
		return user
