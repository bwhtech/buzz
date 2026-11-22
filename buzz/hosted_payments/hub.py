import frappe
import requests
from frappe import _
from frappe.integrations.utils import make_get_request, make_post_request

from buzz.events.buzz_events_listing import buzz_events_headers, buzz_events_method_url

API_PATH = "/api/v2/method/buzz.api.hosted_payments"


def call_hub(method: str, http_method: str = "GET", **arguments):
	"""Call a hosted payments endpoint on buzz.events and return its payload."""
	settings = frappe.get_cached_doc("Buzz Settings")
	url = buzz_events_method_url(settings, f"{API_PATH}.{method}")
	headers = buzz_events_headers(settings)
	try:
		if http_method == "POST":
			response = make_post_request(url, headers=headers, json=arguments, timeout=30)
		else:
			response = make_get_request(url, headers=headers, params=arguments, timeout=30)
	except requests.HTTPError as error:
		frappe.throw(hub_error_message(error), title=_("buzz.events"))
	return response["data"]


def hub_error_message(error: requests.HTTPError) -> str:
	try:
		return error.response.json()["errors"][0]["message"]
	except (ValueError, KeyError, IndexError):
		return _("buzz.events could not take this payment. Please try again.")
