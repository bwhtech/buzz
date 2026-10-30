"""PostHog product analytics: page views, session replay and playground funnel events."""

from contextlib import suppress
from urllib.parse import urlparse

import frappe
import requests

from buzz.playground import is_playground, sandbox_of

DEFAULT_HOST = "https://us.i.posthog.com"
PERSONAS = ("organizer", "attendee", "front_desk")


def is_enabled() -> bool:
	"""The same gate as Frappe's Pulse telemetry, so the site owner's opt-out also covers PostHog."""
	if not frappe.conf.get("posthog_api_key"):
		return False
	if frappe.conf.get("posthog_force_enabled"):
		return True
	return not frappe.conf.get("developer_mode") and bool(frappe.get_system_settings("enable_telemetry"))


def posthog_config() -> dict | None:
	if not is_enabled():
		return None
	sandbox = sandbox_of(frappe.session.user) if is_playground() else None
	return {
		"api_key": frappe.conf.posthog_api_key,
		"host": host(),
		"sandbox": sandbox,
		"persona": sandbox and persona_of(sandbox, frappe.session.user),
	}


def persona_of(sandbox: str, user: str) -> str | None:
	users = frappe.db.get_value("Playground Sandbox", sandbox, PERSONAS, as_dict=True)
	return next((persona for persona, persona_user in users.items() if persona_user == user), None)


def capture(event: str, distinct_id: str, properties: dict | None = None) -> None:
	with suppress(Exception):
		if not is_enabled():
			return
		payload = {
			"api_key": frappe.conf.posthog_api_key,
			"event": event,
			"distinct_id": distinct_id,
			"properties": {"$host": urlparse(frappe.utils.get_url()).netloc, **(properties or {})},
		}
		frappe.enqueue(send, payload=payload, queue="short", enqueue_after_commit=True)


def send(payload: dict) -> None:
	with suppress(Exception):
		requests.post(f"{host()}/i/v0/e/", json=payload, timeout=5)


def host() -> str:
	return (frappe.conf.get("posthog_host") or DEFAULT_HOST).rstrip("/")
