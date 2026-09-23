import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.events.test_events import create_event
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.www.events import EventListing


class TestEventListing(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		for name, slug in (("Test Category", None), ("Listing Meetups", "listing-meetups")):
			if not frappe.db.exists("Event Category", name):
				frappe.get_doc({"doctype": "Event Category", "name": name, "slug": slug}).insert()
		cls.team = create_owned_team("Listing Team", create_user("listing-owner@example.com", "Owner"))
		create_event("Listed", cls.team, route="listed-event", is_published=1, category="Listing Meetups")
		create_event("Unlisted", cls.team, route="unlisted-event", is_published=0)
		create_event(
			"Past",
			cls.team,
			route="past-event",
			is_published=1,
			start_date=add_days(today(), -10),
			end_date=add_days(today(), -9),
		)

	def routes(self, category_slug=None) -> set[str]:
		return {card["url"] for card in EventListing(category_slug).as_context()["events"]}

	def test_lists_only_published_upcoming_events(self):
		routes = self.routes()
		self.assertIn("/events/listed-event", routes)
		self.assertNotIn("/events/unlisted-event", routes)
		self.assertNotIn("/events/past-event", routes)

	def test_category_filter(self):
		self.assertEqual(self.routes("listing-meetups"), {"/events/listed-event"})

	def test_unknown_category_is_not_found(self):
		with self.assertRaises(frappe.PageDoesNotExistError):
			EventListing("no-such-category")
