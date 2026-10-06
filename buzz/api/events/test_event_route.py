import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events import check_event_route
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, UserFactory


class TestCheckEventRoute(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("check-route-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name

	def setUp(self):
		self.route = f"route-{frappe.generate_hash(length=8)}"

	def test_an_unused_route_is_available(self):
		self.assertTrue(self.check(self.route).available)

	def test_a_route_another_event_holds_is_taken(self):
		BuzzEventFactory.create(team=self.team, route=self.route)

		self.assertFalse(self.check(self.route).available)

	def test_an_unpublished_event_still_holds_its_route(self):
		BuzzEventFactory.create("unpublished", team=self.team, route=self.route)

		self.assertFalse(self.check(self.route).available)

	def test_an_event_does_not_block_its_own_route(self):
		event = str(BuzzEventFactory.create(team=self.team, route=self.route).name)

		self.assertTrue(self.check(self.route, event=event).available)

	def test_a_reserved_route_is_refused(self):
		self.assertFalse(self.check("account").available)

	def test_a_blank_route_is_not_available(self):
		self.assertFalse(self.check("   ").available)

	def check(self, route: str, event: str | None = None):
		with self.set_user(self.owner):
			return check_event_route(route, event=event)
