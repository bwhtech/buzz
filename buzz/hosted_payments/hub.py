from buzz.events.buzz_events_client import BuzzEventsClient

API_PATH = "buzz.api.hosted_payments"


def call_hub(method: str, http_method: str = "GET", **arguments):
	"""Call a hosted payments endpoint on buzz.events and return its payload."""
	client = BuzzEventsClient()
	if http_method == "POST":
		return client.post(f"{API_PATH}.{method}", arguments)
	return client.get(f"{API_PATH}.{method}", arguments)
