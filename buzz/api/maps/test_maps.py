from unittest.mock import Mock, patch

import frappe
import requests
from frappe.tests import IntegrationTestCase

from buzz.api.maps import search_places
from buzz.api.maps.exceptions import CannotAddVenues, PlaceSearchFailed, PlaceSearchNotEnabled
from buzz.api.maps.services import place_search_enabled
from buzz.events.doctype.buzz_team.test_buzz_team import create_user

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

	@patch("buzz.api.maps.services.requests.post")
	def test_maps_suggestions_to_predictions_with_the_secret_key(self, post):
		post.return_value = google_answers(SUGGESTIONS)

		places = [place.__json__() for place in search_places("nehru", "token-1")]

		self.assertEqual(
			places, [{"place_id": "place-1", "name": "Nehru Centre", "address": "Worli, Mumbai"}]
		)
		self.assertEqual(post.call_args.kwargs["headers"], {"X-Goog-Api-Key": "secret-places-key"})
		self.assertEqual(post.call_args.kwargs["json"], {"input": "nehru", "sessionToken": "token-1"})

	@patch("buzz.api.maps.services.requests.post")
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

	@patch("buzz.api.maps.services.requests.post", side_effect=requests.ConnectionError)
	def test_google_failure_is_a_named_error(self, post):
		with self.assertRaises(PlaceSearchFailed):
			search_places("nehru", "token-1")

	def test_someone_who_cannot_add_venues_is_refused(self):
		frappe.set_user(create_user("no-venues@example.com", "Attendee"))

		with self.assertRaises(CannotAddVenues):
			search_places("nehru", "token-1")
