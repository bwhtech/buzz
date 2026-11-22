import base64
from unittest.mock import patch

import frappe
import requests
from bwh_payments.services import GatewayUnavailableError
from frappe.tests import IntegrationTestCase

from buzz.events.buzz_events_client import BuzzEventsClient
from buzz.tests.utils import hub_response

REQUEST = "requests.Session.request"
SETTINGS = {
	"buzz_events_url": "https://hub.example.com/",
	"buzz_events_api_key": "pro-key",
	"buzz_events_api_secret": "pro-secret",
}


class TestBuzzEventsClient(IntegrationTestCase):
	def setUp(self):
		self.enterContext(self.change_settings("Buzz Settings", SETTINGS))
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")

	def test_post_calls_the_v2_method_path(self):
		with patch(REQUEST, return_value=hub_response(200, {"data": {"order_id": "HP-1"}})) as request:
			data = BuzzEventsClient().post("buzz.api.hosted_payments.create_order", {"amount": 550})
		self.assertEqual(data, {"order_id": "HP-1"})
		self.assertEqual(
			request.call_args.args,
			("POST", "https://hub.example.com/api/v2/method/buzz.api.hosted_payments.create_order"),
		)
		self.assertEqual(request.call_args.kwargs["json"], {"amount": 550})

	def test_get_sends_the_arguments_as_query_parameters(self):
		with patch(REQUEST, return_value=hub_response(200, {"data": "Paid"})) as request:
			status = BuzzEventsClient().get("buzz.api.hosted_payments.get_status", {"order_id": "HP-1"})
		self.assertEqual(status, "Paid")
		self.assertEqual(request.call_args.args[0], "GET")
		self.assertEqual(request.call_args.kwargs["params"], {"order_id": "HP-1"})

	def test_calls_sign_in_with_the_integration_key_and_time_out(self):
		with patch(REQUEST, return_value=hub_response(200, {"data": None})) as request:
			BuzzEventsClient().get("buzz.api.hosted_payments.get_currencies")
		token = base64.b64encode(b"pro-key:pro-secret").decode()
		self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], f"Basic {token}")
		self.assertEqual(request.call_args.kwargs["timeout"], 30)

	def test_hub_error_message_is_shown_as_it_is(self):
		error = {
			"errors": [{"type": "UnsupportedCurrency", "message": "Buzz cannot take payments in <b>USD</b>."}]
		}
		with patch(REQUEST, return_value=hub_response(400, error)):
			with self.assertRaisesRegex(frappe.ValidationError, r"^Buzz cannot take payments in USD\.$"):
				BuzzEventsClient().post("buzz.api.hosted_payments.create_order", {})

	def test_unreachable_hub_gives_a_readable_error(self):
		for answer in (
			{"side_effect": requests.ConnectionError},
			{"return_value": hub_response(502, text="<html>")},
		):
			with self.subTest(answer=answer), patch(REQUEST, **answer):
				with self.assertRaisesRegex(frappe.ValidationError, "buzz.events could not be reached"):
					BuzzEventsClient().get("buzz.api.hosted_payments.get_currencies")

	def test_a_hub_that_may_answer_later_is_reported_unavailable(self):
		for answer in (
			{"side_effect": requests.Timeout},
			{"side_effect": requests.ConnectionError},
			{"return_value": hub_response(429, {"errors": [{"message": "Too many requests"}]})},
			{"return_value": hub_response(502, text="<html>")},
			{"return_value": hub_response(503, {"errors": [{"message": "Down for maintenance"}]})},
		):
			with self.subTest(answer=answer), patch(REQUEST, **answer):
				with self.assertRaisesRegex(GatewayUnavailableError, "buzz.events could not be reached"):
					BuzzEventsClient().get("buzz.api.hosted_payments.get_status", {"order_id": "HP-1"})

	def test_a_success_the_client_cannot_read_is_reported_unavailable(self):
		# The hub may have acted on it, such as made a refund, so it is not a refusal.
		with patch(REQUEST, return_value=hub_response(200, text="<html>")):
			with self.assertRaises(GatewayUnavailableError):
				BuzzEventsClient().post("buzz.api.hosted_payments.refund", {"order_id": "HP-1"})

	def test_a_refusal_the_client_cannot_read_is_not_reported_unavailable(self):
		with patch(REQUEST, return_value=hub_response(404, text="<html>")):
			with self.assertRaises(frappe.ValidationError) as raised:
				BuzzEventsClient().get("buzz.api.hosted_payments.get_status", {"order_id": "HP-1"})
		self.assertNotIsInstance(raised.exception, GatewayUnavailableError)

	def test_a_hub_refusal_is_not_reported_unavailable(self):
		for status in (400, 403, 404, 417):
			refusal = hub_response(status, {"errors": [{"message": "Order not found"}]})
			with self.subTest(status=status), patch(REQUEST, return_value=refusal):
				with self.assertRaises(frappe.ValidationError) as raised:
					BuzzEventsClient().get("buzz.api.hosted_payments.get_status", {"order_id": "HP-1"})
				self.assertNotIsInstance(raised.exception, GatewayUnavailableError)
