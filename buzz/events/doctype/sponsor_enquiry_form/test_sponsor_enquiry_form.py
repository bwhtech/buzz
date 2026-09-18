import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, now_datetime

from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.test_permissions import add_member, create_event


class TestSponsorEnquiryFormClosing(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		suffix = frappe.generate_hash(length=6)
		self.owner = create_user(f"form-owner-{suffix}@example.com", "Owner")
		self.team = create_owned_team(f"Form Team {suffix}", self.owner)
		self.event = create_event(f"Form {suffix}", self.team, is_published=1)
		self.form = self.form_of(self.event)
		self.suffix = suffix

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def form_of(self, event: str):
		return frappe.get_doc("Sponsor Enquiry Form", {"event": event})

	def member(self, team_role: str, team: str | None = None) -> str:
		user = create_user(f"{team_role.lower()}-{frappe.generate_hash(length=6)}@example.com", team_role)
		add_member(team or self.team, user, team_role)
		return user

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
		frappe.set_user(self.member("Manager"))

		self.assertTrue(self.form_of(self.event).set_closed(True))

	def test_outsiders_cannot_write(self):
		other_owner = create_user(f"other-owner-{self.suffix}@example.com", "Other")
		other_team = create_owned_team(f"Other Team {self.suffix}", other_owner)
		outsiders = {
			"viewer": self.member("Viewer"),
			"frontdesk": self.member("Frontdesk"),
			"other team manager": self.member("Manager", other_team),
			"guest": "Guest",
		}
		for label, user in outsiders.items():
			with self.subTest(label):
				frappe.set_user(user)
				form = frappe.get_doc("Sponsor Enquiry Form", self.form.name, check_permission=False)
				with self.assertRaises(frappe.PermissionError):
					form.check_permission("write")
				with self.assertRaises(frappe.PermissionError):
					form.set_closed(True)
