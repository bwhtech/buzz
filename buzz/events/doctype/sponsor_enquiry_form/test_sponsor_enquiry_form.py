import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime

from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory


class TestSponsorEnquiryFormClosing(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		owner = UserFactory.create_once("form-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(owner).name
		cls.manager = cls.add_member("form-manager@example.com", cls.team, "Manager")
		cls.viewer = cls.add_member("form-viewer@example.com", cls.team, "Viewer")
		cls.frontdesk = cls.add_member("form-frontdesk@example.com", cls.team, "Frontdesk")
		other_team = BuzzTeamFactory.create_owned_by().name
		cls.other_team_manager = cls.add_member("form-other-manager@example.com", other_team, "Manager")

	def setUp(self):
		self.event = str(BuzzEventFactory.create(team=self.team).name)
		self.form = self.form_of(self.event)

	def test_closing_and_opening_round_trips(self):
		self.assertFalse(self.form.set_closed(False))
		self.assertTrue(self.form_of(self.event).publish)

		self.assertTrue(self.form.set_closed(True))
		self.assertFalse(self.form_of(self.event).publish)

	def test_opening_clears_a_past_cutoff(self):
		self.form.auto_close_at = add_days(now_datetime(), -1)
		self.form.save()

		self.assertFalse(self.form.set_closed(False))
		self.assertIsNone(self.form_of(self.event).auto_close_at)

	def test_opening_needs_a_published_event(self):
		frappe.db.set_value("Buzz Event", self.event, "is_published", 0)

		with self.assertRaises(frappe.ValidationError):
			self.form.set_closed(False)

	def test_archived_event_stays_closed(self):
		self.form.set_closed(False)
		frappe.get_doc("Buzz Event", self.event).archive_event()
		form = self.form_of(self.event)

		self.assertTrue(form.is_closed)
		with self.assertRaises(frappe.ValidationError):
			form.set_closed(False)

	def test_team_manager_may_toggle(self):
		with self.set_user(self.manager):
			self.assertTrue(self.form_of(self.event).set_closed(True))

	def test_outsiders_cannot_write(self):
		outsiders = {
			"viewer": self.viewer,
			"frontdesk": self.frontdesk,
			"other team manager": self.other_team_manager,
			"guest": "Guest",
		}
		for label, user in outsiders.items():
			with self.subTest(label), self.set_user(user):
				form = frappe.get_doc("Sponsor Enquiry Form", self.form.name, check_permission=False)
				with self.assertRaises(frappe.PermissionError):
					form.check_permission("write")
				with self.assertRaises(frappe.PermissionError):
					form.set_closed(True)

	@classmethod
	def add_member(cls, email: str, team: str, team_role: str) -> str:
		user = UserFactory.create_once(email).name
		BuzzTeamMembershipFactory.create(team=team, user=user, team_role=team_role)
		return user

	def form_of(self, event: str):
		return frappe.get_doc("Sponsor Enquiry Form", {"event": event})
