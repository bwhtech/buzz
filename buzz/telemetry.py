from contextlib import suppress
from functools import partial
from urllib.parse import urlparse

import frappe
from frappe.utils.telemetry import capture as frappe_capture
from frappe.utils.telemetry.pulse.client import is_enabled

import buzz

APP = "buzz"

COUNT_BUCKETS = ((0, "0"), (1, "1"), (5, "2-5"), (20, "6-20"), (100, "21-100"))


def capture(
	event: str, properties: dict | None = None, interval: str | None = None, on_commit: bool = True
) -> None:
	"""Report `event` to Pulse. `on_commit=False` for events no write stands behind."""
	with suppress(Exception):
		if is_system_write() or not is_enabled():
			return

		properties = {**shared_properties(), **(properties or {})}
		if not on_commit:
			return send(event, properties, interval)

		# Pulse queues in Redis right away, so wait for the commit: a rolled-back
		# write must not report an event that never happened.
		frappe.db.after_commit.add(partial(send, event, properties, interval))


def send(event: str, properties: dict, interval: str | None) -> None:
	with suppress(Exception):
		frappe_capture(event, APP, properties=properties, interval=interval)


def is_system_write() -> bool:
	flags = frappe.flags
	return bool(flags.in_install or flags.in_migrate or flags.in_patch or flags.in_fixtures)


def shared_properties() -> dict:
	return {"app_version": buzz.__version__, "entry": get_entry()}


def get_entry() -> str:
	if frappe.flags.in_import:
		return "import"

	request = getattr(frappe.local, "request", None)
	if not request:
		return "system"

	path = urlparse(request.headers.get("Referer") or "").path
	if not path:
		return "api"
	if is_under(path, ("/app", "/desk")):
		return "desk"
	if is_under(path, ("/b",)):
		return "dashboard"
	return "website"


def is_under(path: str, prefixes: tuple[str, ...]) -> bool:
	return any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)


def count_bucket(count: int) -> str:
	for upper, label in COUNT_BUCKETS:
		if count <= upper:
			return label
	return "101+"
