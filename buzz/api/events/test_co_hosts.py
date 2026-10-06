import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events import add_co_host, get_event, remove_co_host
from buzz.api.events.exceptions import CannotManageEvent
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory


class TestEventCoHosts(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("co-host-owner@example.com").name
		cls.viewer = UserFactory.create_once("co-host-viewer@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner, team_name="Co-host Team").name
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.viewer, team_role="Viewer")

	def setUp(self):
		self.event = str(BuzzEventFactory.create(team=self.team).name)
		self.enterContext(self.set_user(self.owner))

	def test_the_team_is_the_primary_host(self):
		detail = get_event(self.event).__json__()

		self.assertEqual(detail["primary_host"]["host"], self.team)
		self.assertEqual(detail["primary_host"]["label"], "Co-host Team")
		self.assertEqual(detail["co_hosts"], [])

	def test_adding_and_removing_a_co_host_round_trips(self):
		added = add_co_host(self.event, "Acme Corp", by_line="We make things")

		self.assertEqual(self.co_hosts()[0]["label"], "Acme Corp")
		self.assertEqual(frappe.db.get_value("Event Host", added.host, "team"), self.team)

		remove_co_host(self.event, added.host)
		self.assertEqual(self.co_hosts(), [])

	def test_the_same_organisation_cannot_be_added_twice(self):
		added = add_co_host(self.event, "Acme Corp")
		event = frappe.get_doc("Buzz Event", self.event)
		event.append("co_hosts", {"host": added.host})

		with self.assertRaises(frappe.ValidationError):
			event.save()

	def test_the_same_name_is_not_added_twice(self):
		added = add_co_host(self.event, "Acme Corp")

		with self.assertRaises(frappe.ValidationError):
			add_co_host(self.event, "Acme Corp")

		# The second call reuses the team's host rather than minting a second record.
		self.assertEqual(frappe.db.count("Event Host", {"host_name": "Acme Corp", "team": self.team}), 1)
		self.assertEqual(self.co_hosts()[0]["host"], added.host)

	def test_external_links_come_back_in_table_order(self):
		self.save_links(
			{"icon": "map-pin", "label": "Venue map", "url": "https://maps.example.com"},
			{"label": "Slides", "url": "https://slides.example.com"},
		)

		links = get_event(self.event).__json__()["external_links"]

		self.assertEqual([link["label"] for link in links], ["Venue map", "Slides"])
		self.assertEqual(links[0]["icon"], "map-pin")
		self.assertIsNone(links[1]["icon"])

	def test_an_external_link_needs_a_valid_url(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_links({"label": "Broken", "url": "not a url"})

	def test_an_external_link_must_be_a_web_address(self):
		with self.assertRaises(frappe.ValidationError):
			self.save_links({"label": "Script", "url": "javascript:alert(1)"})

	def test_a_viewer_cannot_add_a_co_host(self):
		with self.set_user(self.viewer), self.assertRaises(CannotManageEvent):
			add_co_host(self.event, "Acme Corp")

	def test_a_viewer_cannot_remove_a_co_host(self):
		added = add_co_host(self.event, "Acme Corp")

		with self.set_user(self.viewer), self.assertRaises(CannotManageEvent):
			remove_co_host(self.event, added.host)

	def co_hosts(self) -> list[dict]:
		return get_event(self.event).__json__()["co_hosts"]

	def save_links(self, *links: dict):
		event = frappe.get_doc("Buzz Event", self.event)
		for link in links:
			event.append("external_links", link)
		event.save()
