from contextlib import suppress
from urllib.parse import urlparse

import frappe
from frappe.utils.telemetry import capture as frappe_capture

import buzz

APP = "buzz"

COUNT_BUCKETS = ((0, "0"), (1, "1"), (5, "2-5"), (20, "6-20"), (100, "21-100"))


def capture(event: str, properties: dict | None = None, interval: str | None = None) -> None:
	with suppress(Exception):
		if is_system_write():
			return

		frappe_capture(
			event,
			APP,
			properties={**shared_properties(), **(properties or {})},
			interval=interval,
		)


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
	if path.startswith(("/app", "/desk")):
		return "desk"
	if path == "/b" or path.startswith(("/b/", "/dashboard")):
		return "dashboard"
	return "website"


def count_bucket(count: int) -> str:
	for upper, label in COUNT_BUCKETS:
		if count <= upper:
			return label
	return "100+"
