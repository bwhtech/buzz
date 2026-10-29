from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.events.buzz_events_listing import ListingPush, enqueue_push, push_event, source_id_of
from buzz.tests.factories import BuzzEventFactory

POST = "buzz.events.buzz_events_listing.make_post_request"
ENQUEUE = "buzz.events.buzz_events_listing.frappe.enqueue"
SETTINGS = {
	"list_on_buzz_events": 1,
	"buzz_events_url": "https://listings.example.com/",
	"buzz_events_api_key": "key",
	"buzz_events_api_secret": "secret",
}


class TestBuzzEventsListing(IntegrationTestCase):
	def setUp(self):
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")

	def test_payload(self):
		event = BuzzEventFactory.create(title="Launch Night", time_zone="Asia/Kolkata")
		payload = ListingPush(event).payload()
		self.assertEqual(payload["source_id"], f"{frappe.local.site}:{event.name}")
		self.assertEqual(payload["event_title"], "Launch Night")
		self.assertEqual(payload["event_location"], "Online")
		self.assertTrue(payload["start_datetime"].endswith("+05:30"))
		self.assertTrue(payload["event_url"].endswith(f"/events/{event.route}"))

	def test_published_event_is_upserted(self):
		event = BuzzEventFactory.create()
		with self.change_settings("Buzz Settings", SETTINGS), patch(POST) as post:
			push_event(str(event.name))
		url = post.call_args.args[0]
		self.assertEqual(url, "https://listings.example.com/api/v2/method/buzz.api.listings.upsert_event")
		self.assertEqual(post.call_args.kwargs["headers"], {"Authorization": "token key:secret"})
		self.assertEqual(post.call_args.kwargs["json"]["event"]["event_title"], event.title)

	def test_unpublished_or_ended_event_is_removed(self):
		past = add_days(today(), -3)
		for event in (
			BuzzEventFactory.create("unpublished"),
			BuzzEventFactory.create(start_date=past, end_date=past),
		):
			with self.change_settings("Buzz Settings", SETTINGS), patch(POST) as post:
				push_event(str(event.name))
			self.assertTrue(post.call_args.args[0].endswith("remove_event"))
			self.assertEqual(post.call_args.kwargs["json"], {"source_id": source_id_of(event.name)})

	def test_nothing_runs_when_disabled(self):
		event = BuzzEventFactory.create()
		with self.change_settings("Buzz Settings", {"list_on_buzz_events": 0}):
			with patch(POST) as post, patch(ENQUEUE) as enqueue:
				push_event(str(event.name))
				enqueue_push(event)
		post.assert_not_called()
		enqueue.assert_not_called()

	def test_sync_events_queues_a_full_sync(self):
		with self.change_settings("Buzz Settings", SETTINGS), patch(ENQUEUE) as enqueue:
			frappe.get_doc("Buzz Settings").sync_events()
		self.assertEqual(enqueue.call_args.args[0], "buzz.events.buzz_events_listing.sync_all_events")

	def test_sync_events_needs_listing_turned_on(self):
		with self.change_settings("Buzz Settings", {"list_on_buzz_events": 0}), patch(ENQUEUE) as enqueue:
			self.assertRaises(frappe.ValidationError, frappe.get_doc("Buzz Settings").sync_events)
		enqueue.assert_not_called()
