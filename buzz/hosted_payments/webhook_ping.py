import frappe
import requests
from frappe.integrations.utils import make_post_request


def sync_hosted_payment(payment_request, method: str | None = None) -> None:
	"""Mirror a hub payment's status onto its Hosted Payment, then ping the connected site."""
	if payment_request.ref_doctype != "Hosted Payment" or payment_request.flags.in_insert:
		return
	if not payment_request.has_value_changed("status"):
		return
	order_id = payment_request.ref_docname
	frappe.db.set_value("Hosted Payment", order_id, "status", payment_request.status)
	frappe.enqueue(
		ping_site,
		queue="short",
		order_id=order_id,
		webhook_url=frappe.db.get_value("Hosted Payment", order_id, "webhook_url"),
		enqueue_after_commit=True,
	)


def ping_site(order_id: str, webhook_url: str) -> None:
	"""The site re-reads the status from the hub, so a lost ping only waits for the buyer's return."""
	try:
		make_post_request(webhook_url, json={"order_id": order_id}, timeout=30)
	except requests.RequestException:
		pass  # make_post_request has logged it.
