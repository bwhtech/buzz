import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	EventCategoryFactory,
	EventTicketFactory,
	UserFactory,
)
from buzz.www.events import DiscoverPage, EventListing, event_card, hosting_banner_visible, icon_url


class TestEventListing(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("listing-owner@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		cls.slug = f"listing-{frappe.generate_hash(length=8)}"
		category = EventCategoryFactory.create(slug=cls.slug).name
		cls.listed = cls.create_event(category=category)
		cls.unlisted = cls.create_event("unpublished")
		cls.past = cls.create_event(start_date=add_days(today(), -10), end_date=add_days(today(), -9))
		cls.ended_today = cls.create_event(
			category=category,
			start_date=today(),
			end_date=today(),
			start_time="00:00:00",
			end_time="00:00:01",
		)
		cls.live = cls.create_event(start_date=add_days(today(), -1), end_date=add_days(today(), 1))
		cls.quiet = cls.create_event()
		cls.featured = cls.create_event(is_featured=1)
		popular = BuzzEventFactory.create(team=cls.team)
		EventTicketFactory.create_list(2, "submitted", event=popular.name)
		cls.popular = popular.route

	def test_popular_lists_only_published_upcoming_events(self):
		routes = self.popular_routes()
		self.assertIn(self.listed, routes)
		self.assertNotIn(self.unlisted, routes)
		self.assertNotIn(self.past, routes)

	def test_popular_skips_events_that_ended_earlier_today(self):
		self.assertNotIn(self.ended_today, self.popular_routes())

	def test_only_running_events_are_live(self):
		events = {event.route: event for event in DiscoverPage().popular_events(limit=1000)}
		self.assertTrue(event_card(events[self.live])["is_live"])
		self.assertFalse(event_card(events[self.quiet])["is_live"])

	def test_popular_shows_latest_start_date_first(self):
		start_dates = [event.start_date for event in DiscoverPage().popular_events(limit=1000)]
		self.assertEqual(start_dates, sorted(start_dates, reverse=True))

	def test_popular_orders_by_ticket_count(self):
		routes = self.popular_routes()
		self.assertLess(routes.index(self.popular), routes.index(self.quiet))

	def test_featured_lists_only_flagged_events(self):
		routes = [event.route for event in DiscoverPage().featured_events()]
		self.assertIn(self.featured, routes)
		self.assertNotIn(self.listed, routes)

	def test_popular_skips_featured_events(self):
		self.assertNotIn(self.featured, self.popular_routes())

	def test_team_manager_cannot_feature_events(self):
		self.assertIn("Event Manager", frappe.get_roles(self.owner))
		writable = frappe.get_meta("Buzz Event").get_permlevel_access("write", user=self.owner)
		self.assertNotIn(1, writable)

	def test_category_counts_only_published_upcoming_events(self):
		categories = {category["slug"]: category for category in DiscoverPage().categories()}
		self.assertEqual(categories[self.slug]["event_count"], 1)

	def test_icon_url_is_never_markup(self):
		url = icon_url("<svg><script>alert(1)</script></svg>")
		self.assertTrue(url.startswith("data:image/svg+xml,"))
		self.assertNotIn("<", url)
		self.assertEqual(icon_url(None), "")

	def test_category_filter(self):
		routes = {card["url"] for card in EventListing(self.slug).as_context()["events"]}
		self.assertEqual(routes, {f"/events/{self.listed}"})

	def test_category_page_points_at_itself(self):
		url = EventListing(self.slug).as_context()["meta"]["url"]
		self.assertTrue(url.endswith(f"/events?category={self.slug}"))

	def test_unknown_category_is_not_found(self):
		with self.assertRaises(frappe.PageDoesNotExistError):
			EventListing("no-such-category")

	def test_hosting_banner_only_for_guests_with_setting_on(self):
		with self.change_settings("Buzz Settings", show_hosting_banner=1):
			self.assertTrue(hosting_banner_visible(is_guest=True))
			self.assertFalse(hosting_banner_visible(is_guest=False))
		with self.change_settings("Buzz Settings", show_hosting_banner=0):
			self.assertFalse(hosting_banner_visible(is_guest=True))

	@classmethod
	def create_event(cls, *traits: str, **overrides) -> str:
		"""The route, which is what the listings hand back."""
		return BuzzEventFactory.create(*traits, team=cls.team, **overrides).route

	def popular_routes(self) -> list[str]:
		return [event.route for event in DiscoverPage().popular_events(limit=1000)]
