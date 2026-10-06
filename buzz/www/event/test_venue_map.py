import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from buzz.emails import venue_map_url as email_venue_map_url
from buzz.tests.factories import EventVenueFactory
from buzz.www.event.venue_map import google_maps_url, open_street_map_url, venue_map_url


class TestVenueMap(UnitTestCase):
	def test_google_embed_keeps_only_google_source(self):
		embed = '<iframe src="https://www.google.com/maps/embed?pb=abc" onload="alert(1)"></iframe>'
		self.assertEqual(google_maps_url(embed), "https://www.google.com/maps/embed?pb=abc")

	def test_google_embed_rejects_other_hosts(self):
		self.assertIsNone(google_maps_url('<iframe src="https://evil.example/maps/embed"></iframe>'))
		self.assertIsNone(google_maps_url('<iframe src="javascript:alert(1)"></iframe>'))
		self.assertIsNone(google_maps_url("http://www.google.com/maps/embed?pb=abc"))

	def test_open_street_map_needs_coordinates(self):
		self.assertIsNone(open_street_map_url(0, 0))
		self.assertIn("marker=19.0%2C72.8", open_street_map_url(19.0, 72.8))


class TestGooglePlaceMap(IntegrationTestCase):
	PLACE = frappe._dict(google_place_id="place-1", type=None, latitude=0, longitude=0)

	def test_place_with_an_embed_key_gets_the_google_embed(self):
		self.set_google_maps(1, "embed-key")
		self.assertEqual(
			venue_map_url(self.PLACE),
			"https://www.google.com/maps/embed/v1/place?key=embed-key&q=place_id%3Aplace-1",
		)

	def test_place_without_an_embed_key_has_no_map(self):
		self.set_google_maps(1, None)
		self.assertIsNone(venue_map_url(self.PLACE))

	def test_place_with_the_switch_off_has_no_map(self):
		self.set_google_maps(0, "embed-key")
		self.assertIsNone(venue_map_url(self.PLACE))

	def test_venue_without_a_place_keeps_its_own_map(self):
		self.set_google_maps(1, "embed-key")
		venue = frappe._dict(google_place_id=None, type="Open Street Map", latitude=19.0, longitude=72.8)
		self.assertIn("openstreetmap.org", venue_map_url(venue))

	def test_email_link_points_at_the_place(self):
		venue = EventVenueFactory.create(
			venue_name="Nehru Centre", address="Worli", google_place_id="place-1"
		)
		self.assertEqual(
			email_venue_map_url(venue.name),
			"https://www.google.com/maps/search/?api=1&query=Nehru+Centre&query_place_id=place-1",
		)

	def set_google_maps(self, enabled: int, embed_key: str | None):
		self.enterContext(
			self.change_settings(
				"Buzz Settings", google_maps_enabled=enabled, google_maps_embed_api_key=embed_key
			)
		)
