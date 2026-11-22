from unittest.mock import patch

import frappe
import requests
from frappe.utils import add_to_date, get_datetime, now_datetime

from buzz.api.hosted_payments import create_order
from buzz.hosted_payments.webhook_ping import MAX_PING_ATTEMPTS, ping_site, retry_due_pings
from buzz.tests.base_test_cases import HostedPaymentsTestCase
from buzz.tests.utils import hub_response

SITE_ANSWERS = {"return_value": hub_response(200, {"status": "ok"})}
SITE_IS_DOWN = {"return_value": hub_response(503, text="Service Unavailable")}


def enqueued_pings(action) -> list[str]:
	with patch("frappe.enqueue") as enqueue:
		action()
	return [call.kwargs["order_id"] for call in enqueue.call_args_list if call.args[0] is ping_site]


class TestSitePingRetry(HostedPaymentsTestCase):
	def setUp(self):
		super().setUp()
		with self.set_user(self.integration):
			self.order_id = create_order(**self.order_values()).order_id
		self.enterContext(patch("frappe.log_error"))

	def ping(self, answer: dict) -> None:
		webhook_url = frappe.db.get_value("Hosted Payment", self.order_id, "webhook_url")
		with patch("requests.Session.request", **answer):
			ping_site(order_id=self.order_id, webhook_url=webhook_url)

	def ping_state(self) -> tuple:
		fields = ["ping_status", "ping_attempts", "next_ping_on"]
		return frappe.db.get_value("Hosted Payment", self.order_id, fields)

	def minutes_to_next_ping(self) -> float:
		return (get_datetime(self.ping_state()[2]) - now_datetime()).total_seconds() / 60

	def test_ping_the_site_answers_is_delivered(self):
		self.ping(SITE_ANSWERS)
		self.assertEqual(self.ping_state(), ("Delivered", 0, None))

	def test_ping_the_site_does_not_answer_is_retried_after_a_growing_delay(self):
		delays = []
		for _ in range(3):
			with self.freeze_time(now_datetime()):
				self.ping(SITE_IS_DOWN)
				delays.append(self.minutes_to_next_ping())
		self.assertEqual(delays, [2, 4, 8])
		self.assertEqual(self.ping_state()[:2], ("Pending", 3))

	def test_retry_delay_is_capped_at_an_hour(self):
		frappe.db.set_value("Hosted Payment", self.order_id, "ping_attempts", 6)
		with self.freeze_time(now_datetime()):
			self.ping(SITE_IS_DOWN)
			self.assertEqual(self.minutes_to_next_ping(), 60)

	def test_ping_that_keeps_failing_is_left_for_an_operator(self):
		frappe.db.set_value("Hosted Payment", self.order_id, "ping_attempts", MAX_PING_ATTEMPTS - 1)
		self.ping(SITE_IS_DOWN)
		self.assertEqual(self.ping_state(), ("Failed", MAX_PING_ATTEMPTS, None))

	def test_due_ping_is_sent_again_and_one_not_due_waits(self):
		self.ping(SITE_IS_DOWN)
		self.assertNotIn(self.order_id, enqueued_pings(retry_due_pings))
		with self.freeze_time(add_to_date(now_datetime(), minutes=3)):
			self.assertIn(self.order_id, enqueued_pings(retry_due_pings))

	def test_delivered_ping_is_not_sent_again(self):
		self.ping(SITE_ANSWERS)
		with self.freeze_time(add_to_date(now_datetime(), hours=2)):
			self.assertNotIn(self.order_id, enqueued_pings(retry_due_pings))

	def test_operator_pings_a_failed_site_again(self):
		frappe.db.set_value("Hosted Payment", self.order_id, "ping_attempts", MAX_PING_ATTEMPTS - 1)
		self.ping(SITE_IS_DOWN)
		payment = frappe.get_doc("Hosted Payment", self.order_id)
		self.assertEqual(enqueued_pings(payment.ping_site_again), [self.order_id])
		self.assertEqual(self.ping_state()[:2], ("Pending", 0))
