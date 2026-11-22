import frappe
import requests
from frappe import _
from frappe.frappeclient import FrappeClient
from frappe.utils import strip_html

TIMEOUT_SECONDS = 30


class BuzzEventsClient(FrappeClient):
	"""This site's calls to buzz.events, signed in as its team's Integration user.

	FrappeClient's get_api and post_api use the v1 /api/method/ path and no timeout, so these use v2.
	"""

	def __init__(self):
		settings = frappe.get_cached_doc("Buzz Settings")
		super().__init__(
			settings.buzz_events_url.rstrip("/"),
			api_key=settings.buzz_events_api_key,
			api_secret=settings.get_password("buzz_events_api_secret"),
		)

	def get(self, method: str, params: dict | None = None):
		return self.request("GET", method, params=params)

	def post(self, method: str, body: dict):
		headers = {**self.headers, "content-type": "application/json"}
		return self.request("POST", method, json=body, headers=headers)

	def request(self, http_method: str, method: str, **options):
		options.setdefault("headers", self.headers)
		try:
			response = self.session.request(
				http_method,
				f"{self.url}/api/v2/method/{method}",
				verify=self.verify,
				timeout=TIMEOUT_SECONDS,
				**options,
			)
			return self.read(response)
		except (requests.RequestException, ValueError):
			frappe.throw(_("buzz.events could not be reached. Please try again."), title=_("buzz.events"))

	def read(self, response: requests.Response):
		"""The hub's own error message reaches the buyer as it is."""
		errors = response.json().get("errors") or []
		if errors and errors[0].get("message"):
			frappe.throw(strip_html(errors[0]["message"]), title=_("buzz.events"))
		return self.post_process(response)
