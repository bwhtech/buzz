from frappe.tests import IntegrationTestCase

from buzz.api.teams import create_personal_team, get_my_teams
from buzz.api.teams.exceptions import PersonalTeamsDisabled
from buzz.tests.factories import UserFactory


class TestCreatePersonalTeam(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.user = UserFactory.create_once("personal-team-api@example.com").name

	def setUp(self):
		self.enterContext(self.change_settings("Buzz Settings", enable_personal_teams=1))
		self.enterContext(self.set_user(self.user))

	def test_personal_team_is_listed_as_personal_in_my_teams(self):
		team = create_personal_team()

		personal = [option.name for option in get_my_teams() if option.is_personal]
		self.assertEqual(personal, [team])

	def test_creating_twice_returns_the_same_team(self):
		self.assertEqual(create_personal_team(), create_personal_team())

	def test_refused_while_personal_teams_are_off(self):
		with self.change_settings("Buzz Settings", enable_personal_teams=0):
			self.assertRaises(PersonalTeamsDisabled, create_personal_team)
