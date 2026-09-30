from unittest.mock import Mock, patch

import frappe
import requests
from frappe.tests import IntegrationTestCase

from buzz.api.maps import add_place_as_venue, locate_map_link, search_places
from buzz.api.maps.exceptions import CannotAddVenues, PlaceSearchFailed, PlaceSearchNotEnabled
from buzz.api.maps.services import place_search_enabled
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.events.doctype.event_venue.test_event_venue import clear_map_link_cache

SUGGESTIONS = {
	"suggestions": [
		{
			"placePrediction": {
				"placeId": "place-1",
				"text": {"text": "Nehru Centre, Worli, Mumbai"},
				"structuredFormat": {
					"mainText": {"text": "Nehru Centre"},
					"secondaryText": {"text": "Worli, Mumbai"},
				},
			}
		},
		{"queryPrediction": {"text": {"text": "nehru centre events"}}},
	]
}


def configure_google_maps(enabled: int = 1, places_key: str | None = "secret-places-key") -> None:
	settings = frappe.get_doc("Buzz Settings")
	settings.google_maps_enabled = enabled
	settings.google_places_api_key = places_key
	settings.save()


def google_answers(payload: dict) -> Mock:
	return Mock(json=Mock(return_value=payload), raise_for_status=Mock())


class TestSearchPlaces(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")
		configure_google_maps()

	@patch("buzz.api.maps.services.requests.request")
	def test_maps_suggestions_to_predictions_with_the_secret_key(self, post):
		post.return_value = google_answers(SUGGESTIONS)

		places = [place.__json__() for place in search_places("nehru", "token-1")]

		self.assertEqual(
			places, [{"place_id": "place-1", "name": "Nehru Centre", "address": "Worli, Mumbai"}]
		)
		self.assertEqual(
			post.call_args.args, ("POST", "https://places.googleapis.com/v1/places:autocomplete")
		)
		self.assertEqual(post.call_args.kwargs["headers"], {"X-Goog-Api-Key": "secret-places-key"})
		self.assertEqual(post.call_args.kwargs["json"], {"input": "nehru", "sessionToken": "token-1"})

	@patch("buzz.api.maps.services.requests.request")
	def test_blank_query_does_not_call_google(self, post):
		self.assertEqual(search_places("  ", "token-1"), [])
		post.assert_not_called()

	def test_disabled_switch_turns_search_off(self):
		configure_google_maps(enabled=0)

		self.assertFalse(place_search_enabled())
		with self.assertRaises(PlaceSearchNotEnabled):
			search_places("nehru", "token-1")

	def test_missing_key_turns_search_off(self):
		configure_google_maps(places_key=None)

		self.assertFalse(place_search_enabled())
		with self.assertRaises(PlaceSearchNotEnabled):
			search_places("nehru", "token-1")

	@patch("buzz.api.maps.services.requests.request", side_effect=requests.ConnectionError)
	def test_google_failure_is_a_named_error(self, post):
		with self.assertRaises(PlaceSearchFailed):
			search_places("nehru", "token-1")

	def test_someone_who_cannot_add_venues_is_refused(self):
		frappe.set_user(create_user("no-venues@example.com", "Attendee"))

		with self.assertRaises(CannotAddVenues):
			search_places("nehru", "token-1")


class TestAddPlaceAsVenue(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = create_user("place-venue-owner@example.com", "Owner")
		cls.team = create_owned_team("Place Venue Team", cls.owner)

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")
		configure_google_maps()
		frappe.set_user(self.owner)

	@patch("buzz.api.maps.services.requests.request")
	def test_saves_the_place_with_its_address_and_place_id(self, request):
		request.return_value = google_answers(
			{"id": "place-1", "formattedAddress": "Dr Annie Besant Rd, Worli"}
		)

		venue = frappe.get_doc(
			"Event Venue", add_place_as_venue(self.team, "place-1", "Nehru Centre", "token-1")
		)

		self.assertEqual(
			(venue.venue_name, venue.address, venue.google_place_id, venue.team),
			("Nehru Centre", "Dr Annie Besant Rd, Worli", "place-1", self.team),
		)
		self.assertFalse(venue.latitude or venue.longitude)
		self.assertEqual(request.call_args.args, ("GET", "https://places.googleapis.com/v1/places/place-1"))
		self.assertEqual(request.call_args.kwargs["params"], {"sessionToken": "token-1"})
		self.assertEqual(request.call_args.kwargs["headers"]["X-Goog-FieldMask"], "id,formattedAddress")

	@patch("buzz.api.maps.services.requests.request")
	def test_a_place_the_team_already_has_is_reused_without_calling_google(self, request):
		request.return_value = google_answers({"formattedAddress": "Somewhere"})
		first = add_place_as_venue(self.team, "place-2", "Town Hall", "token-1")

		self.assertEqual(add_place_as_venue(self.team, "place-2", "Town Hall", "token-2"), first)
		request.assert_called_once()

	@patch("buzz.api.maps.services.requests.request")
	def test_place_id_cannot_redirect_the_google_call(self, request):
		request.return_value = google_answers({})

		add_place_as_venue(self.team, "../other?x=1", "Odd Place", "token-1")

		self.assertEqual(
			request.call_args.args[1], "https://places.googleapis.com/v1/places/..%2Fother%3Fx%3D1"
		)

	@patch("buzz.api.maps.services.requests.request")
	def test_another_teams_member_cannot_add_to_the_team(self, request):
		request.return_value = google_answers({"formattedAddress": "Somewhere"})
		outsider = create_user("place-venue-outsider@example.com", "Outsider")
		create_owned_team("Place Venue Other Team", outsider)
		frappe.set_user(outsider)

		with self.assertRaises(frappe.PermissionError):
			add_place_as_venue(self.team, "place-3", "Not Mine", "token-1")
		request.assert_not_called()


class TestLocateMapLink(IntegrationTestCase):
	def setUp(self):
		clear_map_link_cache()
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_google_link_gives_coordinates_and_the_place_name(self):
		link = "https://www.google.com/maps/place/Nehru+Centre/@18.99,72.81,17z/data=!3d18.9903!4d72.8174"

		self.assertEqual(
			locate_map_link(link).__json__(),
			{
				"latitude": 18.9903,
				"longitude": 72.8174,
				"name": "Nehru Centre",
				"address": None,
				"embed_url": None,
			},
		)

	def test_embed_code_gives_the_embed_url(self):
		embed = '<iframe src="https://www.google.com/maps/embed?pb=abc"></iframe>'

		self.assertEqual(locate_map_link(embed).embed_url, "https://www.google.com/maps/embed?pb=abc")

	def test_unreadable_link_gives_nothing(self):
		self.assertEqual(
			locate_map_link("https://example.com/somewhere").__json__(),
			{"latitude": None, "longitude": None, "name": None, "address": None, "embed_url": None},
		)

	def test_someone_who_cannot_add_venues_is_refused(self):
		frappe.set_user(create_user("no-map-links@example.com", "Attendee"))

		with self.assertRaises(CannotAddVenues):
			locate_map_link("https://www.openstreetmap.org/#map=17/12.9/77.5")
