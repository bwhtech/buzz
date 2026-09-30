# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

from unittest.mock import Mock, patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events.test_events import create_event
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.events.doctype.event_venue.map_link import SHORT_LINK_DIGITS, coordinates_of, read_map_link
from buzz.patches.set_event_venue_name import execute as set_event_venue_name


class IntegrationTestEventVenue(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.team = create_owned_team("Venue Naming Team", create_user("venue-naming@example.com", "Owner"))

	def create_venue(self, venue_name: str):
		return frappe.get_doc(
			{
				"doctype": "Event Venue",
				"venue_name": venue_name,
				"address": "1 Test Street",
				"team": self.team,
			}
		).insert(ignore_permissions=True)

	def test_name_is_random_and_venue_name_is_the_label(self):
		venue = self.create_venue("Town Hall")

		self.assertNotEqual(venue.name, "Town Hall")
		self.assertEqual(venue.get_title(), "Town Hall")

	def test_two_venues_can_share_a_venue_name(self):
		self.assertNotEqual(self.create_venue("Shared Hall").name, self.create_venue("Shared Hall").name)

	def test_event_reads_the_current_venue_name(self):
		venue = self.create_venue("Old Hall")
		event = frappe.get_doc("Buzz Event", create_event("Venue Name Event", self.team, venue=venue.name))
		self.assertEqual(event.get_venue_name(), "Old Hall")

		venue.venue_name = "New Hall"
		venue.save(ignore_permissions=True)

		self.assertEqual(event.get_venue_name(), "New Hall")

	def test_patch_copies_the_old_docname_into_venue_name(self):
		venue = self.create_venue("Legacy Hall")
		frappe.db.set_value("Event Venue", venue.name, "venue_name", "", update_modified=False)

		set_event_venue_name()

		self.assertEqual(frappe.db.get_value("Event Venue", venue.name, "venue_name"), venue.name)


GOOGLE_PLACE_LINK = (
	"https://www.google.com/maps/place/Nehru+Centre/@18.99,72.81,17z/data=!3m1!4b1!4m6!3m5"
	"!1s0x3be7ce8d!8m2!3d18.9903!4d72.8174!16zL20vMGZf"
)


def open_street_map_short_code(latitude: float, longitude: float, zoom: int) -> str:
	"""OpenStreetMap's own encoding, kept here so the decoder is checked against the real scheme."""
	x = int((longitude + 180) * 2**32 / 360)
	y = int((latitude + 90) * 2**32 / 180)
	interleaved = 0
	for bit in range(31, -1, -1):
		interleaved = (interleaved << 2) | (((x >> bit) & 1) << 1) | ((y >> bit) & 1)
	length = -(-(zoom + 8) // 3)
	code = "".join(SHORT_LINK_DIGITS[(interleaved >> (58 - 6 * index)) & 0x3F] for index in range(length))
	return code + "-" * ((zoom + 8) % 3)


class TestMapLinkCoordinates(IntegrationTestCase):
	def test_google_link_gives_the_place_not_the_map_centre(self):
		self.assertEqual(coordinates_of(GOOGLE_PLACE_LINK), (18.9903, 72.8174))

	def test_google_link_without_a_place_gives_the_map_centre(self):
		self.assertEqual(
			coordinates_of("https://www.google.co.in/maps/@12.9716,77.5946,15z"), (12.9716, 77.5946)
		)

	def test_open_street_map_marker_and_view(self):
		marker = "https://www.openstreetmap.org/?mlat=12.5&mlon=77.5#map=17/1.0/2.0"
		self.assertEqual(coordinates_of(marker), (12.5, 77.5))
		self.assertEqual(
			coordinates_of("https://www.openstreetmap.org/#map=17/12.9716/77.5946"), (12.9716, 77.5946)
		)

	def test_links_without_coordinates_give_nothing(self):
		for link in (
			"https://www.openstreetmap.org/user/someone",
			"https://example.com/@12.9,77.5",
			"https://www.google.com/maps/@999,77.5,15z",
			"not a link",
			None,
		):
			with self.subTest(link=link):
				self.assertIsNone(coordinates_of(link))

	@patch("buzz.events.doctype.event_venue.map_link.requests.get")
	def test_google_short_link_is_followed_one_hop(self, get):
		get.return_value = Mock(headers={"Location": GOOGLE_PLACE_LINK})

		self.assertEqual(coordinates_of("https://maps.app.goo.gl/abc123"), (18.9903, 72.8174))
		get.assert_called_once()
		self.assertFalse(get.call_args.kwargs["allow_redirects"])

	def test_open_street_map_short_link_is_decoded_without_a_request(self):
		code = open_street_map_short_code(latitude=12.9716, longitude=77.5946, zoom=17)

		latitude, longitude = coordinates_of(f"https://osm.org/go/{code}?m=")

		self.assertAlmostEqual(latitude, 12.9716, places=3)
		self.assertAlmostEqual(longitude, 77.5946, places=3)

	@patch("buzz.events.doctype.event_venue.map_link.requests.get")
	def test_open_street_map_object_is_looked_up_by_id(self, get):
		found = [
			{
				"lat": "18.9903",
				"lon": "72.8174",
				"name": "Nehru Centre",
				"display_name": "Nehru Centre, Worli",
			}
		]
		get.return_value = Mock(json=Mock(return_value=found), raise_for_status=Mock())

		place = read_map_link("https://www.openstreetmap.org/way/4567#map=18/1/2")

		self.assertEqual(place, ((18.9903, 72.8174), "Nehru Centre", "Nehru Centre, Worli"))
		self.assertEqual(get.call_args.args, ("https://nominatim.openstreetmap.org/lookup",))
		self.assertEqual(get.call_args.kwargs["params"], {"osm_ids": "W4567", "format": "jsonv2"})

	@patch("buzz.events.doctype.event_venue.map_link.requests.get")
	def test_unknown_open_street_map_object_gives_nothing(self, get):
		get.return_value = Mock(json=Mock(return_value=[]), raise_for_status=Mock())

		self.assertIsNone(coordinates_of("https://www.openstreetmap.org/node/1"))

	@patch("buzz.events.doctype.event_venue.map_link.requests.get")
	def test_other_hosts_are_never_requested(self, get):
		self.assertIsNone(coordinates_of("https://internal.example/maps/abc"))
		get.assert_not_called()


class TestVenueMapLink(IntegrationTestCase):
	def venue(self, **fields):
		return frappe.get_doc({"doctype": "Event Venue", "venue_name": "Linked Hall", **fields})

	def test_map_link_sets_the_location_and_makes_address_optional(self):
		venue = self.venue(map_link=GOOGLE_PLACE_LINK).insert(ignore_permissions=True)

		self.assertEqual((venue.type, venue.latitude, venue.longitude), ("Open Street Map", 18.9903, 72.8174))
		self.assertFalse(venue.address)

	def test_pasted_embed_code_becomes_the_google_embed(self):
		embed = '<iframe src="https://www.google.com/maps/embed?pb=abc" width="600"></iframe>'
		venue = self.venue(map_link=embed).insert(ignore_permissions=True)

		self.assertEqual(venue.type, "Embed Google Maps")
		self.assertIn("maps/embed?pb=abc", venue.google_maps_embed_code)

	def test_address_is_required_when_the_link_shows_no_location(self):
		with self.assertRaises(frappe.ValidationError):
			self.venue(map_link="https://www.openstreetmap.org/user/someone").insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			self.venue().insert(ignore_permissions=True)
