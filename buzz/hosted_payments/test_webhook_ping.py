from unittest.mock import patch

import frappe
import requests
from frappe.utils import add_to_date, get_datetime, now_datetime

from buzz.api.hosted_payments import create_order
from buzz.hosted_payments.webhook_ping import MAX_PING_ATTEMPTS, enqueue_ping, ping_site, retry_due_pings
from buzz.tests.base_test_cases import HostedPaymentsTestCase
from buzz.tests.utils import hub_response

SITE_ANSWERS = {"return_value": hub_response(200, {"status": "ok"})}
SITE_IS_DOWN = {"return_value": hub_response(503, text="Service Unavailable")}


def enqueued_ping_jobs(action) -> list[dict]:
	with patch("frappe.enqueue") as enqueue:
		action()
	jobs = [call.kwargs for call in enqueue.call_args_list if call.args[0] is ping_site]
	return [{key: job[key] for key in ("order_id", "webhook_url", "generation")} for job in jobs]


def enqueued_pings(action) -> list[str]:
	return [job["order_id"] for job in enqueued_ping_jobs(action)]


class TestSitePingRetry(HostedPaymentsTestCase):
	def setUp(self):
		super().setUp()
		with self.set_user(self.integration):
			self.order_id = create_order(**self.order_values()).order_id
		self.enterContext(patch("frappe.log_error"))

	def ping(self, answer: dict, job: dict | None = None) -> None:
		"""Run a ping job: `job`, or a retry of the latest delivery."""
		with patch("requests.Session.request", **answer):
			ping_site(**(job or self.latest_delivery()))

	def latest_delivery(self) -> dict:
		fields = ["webhook_url", "ping_generation"]
		webhook_url, generation = frappe.db.get_value("Hosted Payment", self.order_id, fields)
		return {"order_id": self.order_id, "webhook_url": webhook_url, "generation": generation}

	def request_ping(self) -> dict:
		"""A change the site must hear about, such as a refund settling. Returns its ping job."""
		[job] = enqueued_ping_jobs(lambda: enqueue_ping(self.order_id))
		return job

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

	def test_an_older_delivery_answered_late_leaves_a_newer_failed_one_to_be_retried(self):
		paid_ping, refund_ping = self.request_ping(), self.request_ping()
		self.ping(SITE_IS_DOWN, refund_ping)
		self.ping(SITE_ANSWERS, paid_ping)
		self.assertEqual(self.ping_state()[:2], ("Pending", 1))
		self.assertIsNotNone(self.ping_state()[2])

	def test_an_older_delivery_failing_late_does_not_count_against_a_newer_one(self):
		paid_ping, refund_ping = self.request_ping(), self.request_ping()
		self.ping(SITE_ANSWERS, refund_ping)
		self.ping(SITE_IS_DOWN, paid_ping)
		self.assertEqual(self.ping_state(), ("Delivered", 0, None))

	def test_a_retry_carries_the_latest_delivery(self):
		self.ping(SITE_IS_DOWN, self.request_ping())
		latest = self.request_ping()
		self.ping(SITE_IS_DOWN, latest)
		with self.freeze_time(add_to_date(now_datetime(), minutes=3)):
			[retry] = [job for job in enqueued_ping_jobs(retry_due_pings) if job["order_id"] == self.order_id]
		self.ping(SITE_ANSWERS, retry)
		self.assertEqual(self.ping_state(), ("Delivered", 1, None))
