import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.account import get_user_info
from buzz.api.exceptions import NotPermitted
from buzz.api.onboarding import (
	check_username,
	complete_onboarding,
	get_onboarding_state,
	save_community,
	save_first_event,
	save_profile,
)
from buzz.api.onboarding.exceptions import InvalidUsername, UsernameTaken
from buzz.api.onboarding.schemas import FirstEvent
from buzz.api.onboarding.services import STATUS_FIELD, mark_pending_on_signup
from buzz.tests.factories import BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory


class TestOnboarding(IntegrationTestCase):
	def setUp(self):
		self.user = UserFactory.create_once("onboarding-new@example.com")
		self.other = UserFactory.create_once("onboarding-other@example.com")
		frappe.db.set_value("User", self.other.name, "username", "taken-name")
		frappe.db.set_value("User", self.user.name, STATUS_FIELD, None)
		self.enterContext(self.change_settings("Buzz Settings", enable_onboarding=1))
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(self.user.name)

	def status(self) -> str | None:
		return frappe.db.get_value("User", self.user.name, STATUS_FIELD)

	def test_signup_is_pending_only_while_enabled(self):
		mark_pending_on_signup(self.user)
		self.assertEqual(self.status(), "Pending")

		frappe.db.set_value("User", self.user.name, STATUS_FIELD, None)
		with self.change_settings("Buzz Settings", enable_onboarding=0):
			mark_pending_on_signup(self.user)
		self.assertIsNone(self.status())

	def test_user_info_reports_onboarding_until_completed(self):
		self.assertFalse(get_user_info().needs_onboarding)

		mark_pending_on_signup(self.user)
		self.assertTrue(get_user_info().needs_onboarding)

		complete_onboarding()
		self.assertEqual(self.status(), "Completed")
		self.assertFalse(get_user_info().needs_onboarding)

	def test_username_availability(self):
		self.assertFalse(check_username("taken-name").available)
		self.assertFalse(check_username("No Caps").available)
		self.assertTrue(check_username("free-name").available)

	def test_save_profile_rejects_taken_and_invalid_usernames(self):
		with self.assertRaises(UsernameTaken):
			save_profile(first_name="Priya", username="taken-name")
		with self.assertRaises(InvalidUsername):
			save_profile(first_name="Priya", username="a")

	def test_save_profile_updates_user(self):
		save_profile(first_name="Priya", last_name="Raman", username="priya-onboarding")
		saved = frappe.db.get_value(
			"User", self.user.name, ["first_name", "last_name", "username"], as_dict=True
		)
		self.assertEqual(saved, {"first_name": "Priya", "last_name": "Raman", "username": "priya-onboarding"})


class TestOnboardingSetup(IntegrationTestCase):
	def setUp(self):
		self.user = UserFactory.create_once("onboarding-host@example.com")
		self.enterContext(
			self.change_settings("Buzz Settings", enable_communities=1, enable_personal_teams=1)
		)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(self.user.name)

	def test_community_is_created_once_then_edited(self):
		first = save_community(team_name="Clay Club", slug="clay-club-onboarding")
		second = save_community(
			team_name="Clay Collective", slug="clay-collective-onboarding", short_description="Pots"
		)
		self.assertEqual(first, second)
		team = frappe.db.get_value("Buzz Team", second, ["team_name", "slug", "is_published"], as_dict=True)
		self.assertEqual(
			team, {"team_name": "Clay Collective", "slug": "clay-collective-onboarding", "is_published": 1}
		)
		self.assertEqual(get_onboarding_state().community.name, first)

	def test_first_event_is_an_editable_draft(self):
		team = save_community(team_name="Kiln Club", slug="kiln-club-onboarding")
		event = {"team": team, "title": "Glaze night", "start_date": "2027-01-10", "start_time": "18:00:00"}
		first = save_first_event(FirstEvent(**event, medium="In Person", venue_name="Studio 5"))
		second = save_first_event(FirstEvent(**event, medium="Online", event=first))

		self.assertEqual(first, second)
		saved = frappe.get_doc("Buzz Event", second)
		self.assertEqual((saved.is_published, saved.medium, saved.venue), (0, "Online", None))
		self.assertEqual(str(saved.end_time), "19:00:00")
		self.assertEqual(get_onboarding_state().draft_event.name, first)

	def test_another_users_draft_cannot_be_edited(self):
		team = save_community(team_name="Wheel Club", slug="wheel-club-onboarding")
		event = {"team": team, "title": "Throwing", "start_date": "2027-01-10", "start_time": "18:00:00"}
		draft = save_first_event(FirstEvent(**event, medium="Online"))
		frappe.db.set_value("Buzz Event", draft, "owner", "Administrator")
		with self.assertRaises(NotPermitted):
			save_first_event(FirstEvent(**event, medium="Online", event=draft))


class TestInvitedTeam(IntegrationTestCase):
	def test_invitee_sees_the_team_they_joined(self):
		user = UserFactory.create_once("onboarding-invitee@example.com")
		team = BuzzTeamFactory.create_owned_by(team_name="BLR JS")
		BuzzTeamMembershipFactory.create(team=team.name, user=user.name, team_role="Manager")
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user(user.name)

		invited = get_onboarding_state().invited_team
		self.assertEqual((invited.name, invited.team_role, invited.member_count), (team.name, "Manager", 2))


class TestDeferredSignup(IntegrationTestCase):
	def test_booking_signup_defers_onboarding(self):
		user = UserFactory.create_once("onboarding-booker@example.com")
		self.enterContext(self.change_settings("Buzz Settings", enable_onboarding=1))
		frappe.form_dict.skip_onboarding = "1"
		self.addCleanup(frappe.form_dict.pop, "skip_onboarding", None)
		mark_pending_on_signup(user)
		self.assertEqual(frappe.db.get_value("User", user.name, STATUS_FIELD), "Deferred")

	def test_desk_users_skip_onboarding(self):
		user = UserFactory.create_once("onboarding-staff@example.com")
		self.enterContext(self.change_settings("Buzz Settings", enable_onboarding=1))
		frappe.db.set_value("User", user.name, STATUS_FIELD, None)
		mark_pending_on_signup(frappe._dict(name=user.name, user_type="System User"))
		self.assertIsNone(frappe.db.get_value("User", user.name, STATUS_FIELD))
