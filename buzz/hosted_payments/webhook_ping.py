import frappe
import requests
from frappe.integrations.utils import make_post_request
from frappe.utils import add_to_date, cint, now_datetime

# Pinged from Hosted Payment.on_refund_update, which also hears a refund that leaves the status as it was.
REFUND_STATUSES = ("Partially Refunded", "Refunded")
# About five hours of retries before an operator has to ping again.
MAX_PING_ATTEMPTS = 10
MAX_RETRY_MINUTES = 60


def sync_hosted_payment(payment_request, method: str | None = None) -> None:
	"""Mirror a hub payment's status onto its Hosted Payment, then ping the connected site."""
	if payment_request.ref_doctype != "Hosted Payment" or payment_request.flags.in_insert:
		return
	if not payment_request.has_value_changed("status"):
		return
	order_id = payment_request.ref_docname
	frappe.db.set_value("Hosted Payment", order_id, "status", payment_request.status)
	if payment_request.status not in REFUND_STATUSES:
		enqueue_ping(order_id)


def enqueue_ping(order_id: str) -> None:
	"""Pinged now; `retry_due_pings` sends it again if the site has not answered by `next_ping_on`."""
	set_ping_state(order_id, "Pending", attempts=0)
	frappe.enqueue(
		ping_site,
		queue="short",
		order_id=order_id,
		webhook_url=frappe.db.get_value("Hosted Payment", order_id, "webhook_url"),
		enqueue_after_commit=True,
	)


def ping_site(order_id: str, webhook_url: str) -> None:
	"""The site re-reads the status from the hub, so the ping carries only the order."""
	try:
		make_post_request(webhook_url, json={"order_id": order_id}, timeout=30)
	except requests.RequestException:
		record_failed_ping(order_id)  # make_post_request has logged it.
	else:
		frappe.db.set_value("Hosted Payment", order_id, {"ping_status": "Delivered", "next_ping_on": None})


def record_failed_ping(order_id: str) -> None:
	attempts = cint(frappe.db.get_value("Hosted Payment", order_id, "ping_attempts")) + 1
	status = "Failed" if attempts >= MAX_PING_ATTEMPTS else "Pending"
	set_ping_state(order_id, status, attempts)


def set_ping_state(order_id: str, status: str, attempts: int) -> None:
	next_ping_on = None
	if status == "Pending":
		# A fresh ping also gets a retry time, in case its own job never runs.
		next_ping_on = add_to_date(now_datetime(), minutes=min(2 ** max(attempts, 1), MAX_RETRY_MINUTES))
	frappe.db.set_value(
		"Hosted Payment",
		order_id,
		{"ping_status": status, "ping_attempts": attempts, "next_ping_on": next_ping_on},
	)


def retry_due_pings() -> None:
	due = frappe.get_all(
		"Hosted Payment",
		filters={"ping_status": "Pending", "next_ping_on": ["<=", now_datetime()]},
		fields=["name", "webhook_url"],
	)
	for payment in due:
		frappe.enqueue(
			ping_site,
			queue="short",
			job_id=f"hosted_payment_ping::{payment.name}",
			deduplicate=True,
			order_id=payment.name,
			webhook_url=payment.webhook_url,
		)
