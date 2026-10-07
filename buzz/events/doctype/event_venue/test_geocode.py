from unittest.mock import Mock, patch

import frappe
import requests
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.event_venue.geocode import geocode_venue, venues_to_geocode
from buzz.tests.factories import BuzzTeamFactory, EventVenueFactory

REQUESTS_GET = "buzz.events.doctype.event_venue.geocode.requests.get"


def nominatim_answer(payload) -> Mock:
	return Mock(json=Mock(return_value=payload), raise_for_status=Mock())


class TestGeocodeVenue(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.team = BuzzTeamFactory.create_owned_by().name

	def create_venue(self, **values):
		return EventVenueFactory.create(team=self.team, **values)

	@patch(REQUESTS_GET)
	def test_an_address_fills_coordinates_city_and_country(self, get):
		get.return_value = nominatim_answer(
			[{"lat": "19.0596", "lon": "72.8295", "address": {"city": "Mumbai", "country_code": "in"}}]
		)
		venue = self.create_venue(address="Bandstand, Bandra West, Mumbai")

		geocode_venue(venue.name)

		venue.reload()
		self.assertEqual((venue.latitude, venue.longitude), (19.0596, 72.8295))
		self.assertEqual((venue.city, venue.venue_country), ("Mumbai", "India"))
		self.assertIn("/search", get.call_args.args[0])

	@patch(REQUESTS_GET)
	def test_set_values_are_never_overwritten(self, get):
		get.return_value = nominatim_answer(
			{"lat": "12.9", "lon": "77.5", "address": {"town": "Elsewhere", "country_code": "in"}}
		)
		venue = self.create_venue(latitude=12.9699, longitude=77.6391, city="Indiranagar")

		geocode_venue(venue.name)

		venue.reload()
		self.assertEqual((venue.latitude, venue.longitude), (12.9699, 77.6391))
		self.assertEqual((venue.city, venue.venue_country), ("Indiranagar", "India"))
		self.assertIn("/reverse", get.call_args.args[0])

	@patch("buzz.events.doctype.event_venue.geocode.time.sleep")
	@patch(REQUESTS_GET)
	def test_a_street_address_nominatim_misses_falls_back_to_its_locality(self, get, sleep):
		found = [
			{
				"lat": "12.9352",
				"lon": "77.6245",
				"address": {"suburb": "Koramangala", "city": "Bengaluru", "country_code": "in"},
			}
		]
		get.side_effect = [nominatim_answer([]), nominatim_answer(found)]
		venue = self.create_venue(
			address="No. 374, 3rd Block, situated at, Koramangala, Bengaluru, Karnataka 560034, India"
		)

		geocode_venue(venue.name)

		venue.reload()
		self.assertEqual((venue.latitude, venue.city), (12.9352, "Bengaluru"))
		self.assertEqual(
			get.call_args.kwargs["params"]["q"], "Koramangala, Bengaluru, Karnataka 560034, India"
		)

	@patch(REQUESTS_GET, side_effect=requests.ConnectionError)
	def test_a_failed_lookup_leaves_the_venue_as_it_was(self, get):
		venue = self.create_venue(address="Nowhere in particular")

		geocode_venue(venue.name)

		venue.reload()
		self.assertFalse(venue.latitude or venue.venue_country)

	def test_complete_venues_are_not_geocoded_again(self):
		complete = self.create_venue(
			latitude=51.5, longitude=-0.12, city="London", venue_country="United Kingdom"
		)
		incomplete = self.create_venue(address="1 Unknown Road")

		names = venues_to_geocode()

		self.assertIn(incomplete.name, names)
		self.assertNotIn(complete.name, names)

	@patch("buzz.events.doctype.event_venue.event_venue.enqueue_geocode")
	def test_saving_a_new_address_queues_a_lookup(self, enqueue_geocode):
		with patch.object(frappe, "in_test", False):
			venue = self.create_venue(address="2 New Street")

		enqueue_geocode.assert_called_once_with(venue.name)
