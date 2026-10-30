from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.listings import remove_event, upsert_event
from buzz.api.listings.exceptions import NotAnIntegration
from buzz.api.listings.schemas import EventListing
from buzz.api.teams.services import assignable_roles, members_of
from buzz.permissions import has_team_access, my_team_names
from buzz.tests.factories import BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory

REQUEST = "Community Event Request"


class TestPartnerListings(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.curator = UserFactory.create_once("listing-curator@example.com").name
		cls.bot = UserFactory.create_once("listing-bot@example.com").name
		cls.manager = UserFactory.create_once("listing-manager@example.com").name
		cls.community = BuzzTeamFactory.create_owned_by(cls.curator, "community").name
		BuzzTeamMembershipFactory.create(team=cls.community, user=cls.bot, team_role="Integration")
		BuzzTeamMembershipFactory.create(team=cls.community, user=cls.manager, team_role="Manager")

	def listing(self, **overrides) -> EventListing:
		day = add_days(today(), 20)
		values = {
			"source_id": "partner.example.com:7",
			"event_title": "Partner Meetup",
			"host": "Partner",
			"event_location": "Pune",
			"start_datetime": f"{day}T18:00:00+05:30",
			"end_datetime": f"{day}T20:00:00+05:30",
			"event_url": "https://partner.example.com/events/meetup",
		}
		return EventListing(**(values | overrides))

	def request_names(self, source_id: str = "partner.example.com:7") -> list[str]:
		return frappe.get_all(REQUEST, {"community": self.community, "source_id": source_id}, pluck="name")

	def upsert(self, **overrides) -> None:
		with self.set_user(self.bot):
			upsert_event(self.listing(**overrides))

	def test_upsert_creates_an_approved_request(self):
		self.upsert()
		request = frappe.get_doc(REQUEST, self.request_names()[0])
		self.assertEqual(request.status, "Approved")
		self.assertEqual(request.reviewed_by, self.bot)
		self.assertTrue(request.is_external_event)
		self.assertEqual(request.event_title, "Partner Meetup")

	def test_upsert_stores_the_pin(self):
		self.upsert(latitude=18.5204, longitude=73.8567, city="Pune", country="India")
		request = frappe.get_doc(REQUEST, self.request_names()[0])
		self.assertEqual((request.latitude, request.longitude), (18.5204, 73.8567))
		self.assertEqual((request.city, request.country), ("Pune", "India"))

	def test_upsert_without_a_pin_clears_the_old_one(self):
		self.upsert(latitude=18.5204, longitude=73.8567)
		self.upsert()
		self.assertEqual(frappe.db.get_value(REQUEST, self.request_names()[0], "latitude"), 0)

	def test_a_pin_off_the_globe_is_refused(self):
		with self.assertRaises(ValueError):
			self.listing(latitude=91, longitude=0)

	def test_second_upsert_updates_the_same_request(self):
		self.upsert()
		self.upsert(event_title="Renamed Meetup")
		names = self.request_names()
		self.assertEqual(len(names), 1)
		self.assertEqual(frappe.db.get_value(REQUEST, names[0], "event_title"), "Renamed Meetup")

	def test_upsert_stores_system_time(self):
		with patch("buzz.api.listings.services.get_system_timezone", return_value="Asia/Kolkata"):
			self.upsert(start_datetime=f"{add_days(today(), 20)}T12:30:00+00:00")
		start = frappe.db.get_value(REQUEST, self.request_names()[0], "start_datetime")
		self.assertEqual(start.strftime("%H:%M"), "18:00")

	def test_upsert_keeps_a_request_the_community_took_down(self):
		self.upsert()
		frappe.db.set_value(REQUEST, self.request_names()[0], "status", "Rejected")
		self.upsert(event_title="Renamed Meetup")
		request = frappe.get_doc(REQUEST, self.request_names()[0])
		self.assertEqual((request.status, request.event_title), ("Rejected", "Renamed Meetup"))

	def test_remove_deletes_the_request(self):
		self.upsert()
		with self.set_user(self.bot):
			remove_event("partner.example.com:7")
		self.assertEqual(self.request_names(), [])

	def test_remove_of_an_unknown_id_does_nothing(self):
		with self.set_user(self.bot):
			remove_event("partner.example.com:unknown")

	def test_a_manager_is_not_an_integration(self):
		with self.set_user(self.manager), self.assertRaises(NotAnIntegration):
			upsert_event(self.listing())
		with self.set_user(self.manager), self.assertRaises(NotAnIntegration):
			remove_event("partner.example.com:7")

	def test_an_integration_member_has_no_team_access(self):
		self.assertFalse(has_team_access(self.community, "read", self.bot))
		self.assertEqual(my_team_names(self.bot), [])

	def test_integration_members_are_hidden_and_not_assignable(self):
		self.assertNotIn(self.bot, [member.user for member in members_of(self.community)])
		self.assertIn(self.manager, [member.user for member in members_of(self.community)])
		self.assertNotIn("Integration", assignable_roles())

	def test_only_a_system_manager_can_grant_the_role(self):
		team = BuzzTeamFactory.create_owned_by(self.curator).name
		with self.set_user(self.curator), self.assertRaises(frappe.ValidationError):
			BuzzTeamMembershipFactory.create(
				team=team, user=self.manager, team_role="Integration", flags={"ignore_permissions": True}
			)

	def test_only_a_system_manager_can_remove_the_integration(self):
		membership = frappe.db.get_value(
			"Buzz Team Membership", {"team": self.community, "user": self.bot}, "name"
		)
		with self.set_user(self.curator), self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Buzz Team Membership", membership, ignore_permissions=True)
