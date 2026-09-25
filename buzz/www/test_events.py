import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.events.test_events import create_event
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.test_permissions import create_ticket
from buzz.www.events import DiscoverPage, EventListing, hosting_banner_visible, icon_url


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
		cls.owner = "listing-owner@example.com"
		popular = create_event("Popular", cls.team, route="popular-event", is_published=1)
		create_event("Quiet", cls.team, route="quiet-event", is_published=1)
		for _ in range(2):
			create_ticket(popular, cls.owner, submit=True)
		create_event("Featured", cls.team, route="featured-event", is_published=1, is_featured=1)

	def popular_routes(self) -> list[str]:
		return [event.route for event in DiscoverPage().popular_events(limit=1000)]

	def test_popular_lists_only_published_upcoming_events(self):
		routes = self.popular_routes()
		self.assertIn("listed-event", routes)
		self.assertNotIn("unlisted-event", routes)
		self.assertNotIn("past-event", routes)

	def test_popular_orders_by_ticket_count(self):
		routes = self.popular_routes()
		self.assertLess(routes.index("popular-event"), routes.index("quiet-event"))

	def test_featured_lists_only_flagged_events(self):
		routes = [event.route for event in DiscoverPage().featured_events()]
		self.assertIn("featured-event", routes)
		self.assertNotIn("listed-event", routes)

	def test_popular_skips_featured_events(self):
		self.assertNotIn("featured-event", self.popular_routes())

	def test_team_manager_cannot_feature_events(self):
		self.assertIn("Event Manager", frappe.get_roles(self.owner))
		writable = frappe.get_meta("Buzz Event").get_permlevel_access("write", user=self.owner)
		self.assertNotIn(1, writable)

	def test_category_counts_only_published_upcoming_events(self):
		categories = {category["name"]: category for category in DiscoverPage().categories()}
		self.assertEqual(categories["Listing Meetups"]["event_count"], 1)

	def test_icon_url_is_never_markup(self):
		url = icon_url("<svg><script>alert(1)</script></svg>")
		self.assertTrue(url.startswith("data:image/svg+xml,"))
		self.assertNotIn("<", url)
		self.assertEqual(icon_url(None), "")

	def test_category_filter(self):
		routes = {card["url"] for card in EventListing("listing-meetups").as_context()["events"]}
		self.assertEqual(routes, {"/events/listed-event"})

	def test_category_page_points_at_itself(self):
		url = EventListing("listing-meetups").as_context()["meta"]["url"]
		self.assertTrue(url.endswith("/events?category=listing-meetups"))

	def test_unknown_category_is_not_found(self):
		with self.assertRaises(frappe.PageDoesNotExistError):
			EventListing("no-such-category")

	def test_hosting_banner_only_for_guests_with_setting_on(self):
		frappe.db.set_single_value("Buzz Settings", "show_hosting_banner", 1)
		self.assertTrue(hosting_banner_visible(is_guest=True))
		self.assertFalse(hosting_banner_visible(is_guest=False))
		frappe.db.set_single_value("Buzz Settings", "show_hosting_banner", 0)
		self.assertFalse(hosting_banner_visible(is_guest=True))
