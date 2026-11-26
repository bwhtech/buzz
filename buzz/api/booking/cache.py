from collections.abc import Callable

import frappe

from buzz.events.doctype.buzz_form.form_types import APPLIED_TO_BY_FORM_DOCTYPE

BOOKING_METADATA_KEY_PREFIX = "buzz:booking_metadata:v1:"
BOOKING_METADATA_VERSION_PREFIX = "buzz:booking_metadata_ver:v2:"
EVENT_ROUTE_KEY_PREFIX = "buzz:event_route:v1:"
EVENT_ROUTE_VERSION_PREFIX = "buzz:event_route_ver:v2:"
BOOKING_METADATA_TTL_SECONDS = 15 * 60
EVENT_ROUTE_TTL_SECONDS = 15 * 60


class EventBookingCache:
	"""Transaction-safe Redis cache for static per-event booking metadata and route lookups."""

	@staticmethod
	def metadata_version_key(event_id: str | int) -> str:
		return f"{BOOKING_METADATA_VERSION_PREFIX}{event_id}"

	@classmethod
	def metadata_key(cls, event_id: str | int, version: int | None = None) -> str:
		ver = cls._read_version(cls.metadata_version_key(event_id)) if version is None else version
		return f"{BOOKING_METADATA_KEY_PREFIX}{event_id}:v{ver}"

	@staticmethod
	def route_version_key(route: str) -> str:
		return f"{EVENT_ROUTE_VERSION_PREFIX}{route}"

	@classmethod
	def route_key(cls, route: str, version: int | None = None) -> str:
		ver = cls._read_version(cls.route_version_key(route)) if version is None else version
		return f"{EVENT_ROUTE_KEY_PREFIX}{route}:v{ver}"

	@staticmethod
	def _read_version(version_key: str) -> int:
		key = frappe.cache.make_key(version_key)
		# Tenant-scoped via make_key; raw get reads the unpickled integer written by atomic incr.
		raw = frappe.cache.get(key)  # nosemgrep: frappe-cache-breaks-multitenancy
		return int(raw) if raw is not None else 0

	@staticmethod
	def _bump_version(version_key: str) -> None:
		frappe.cache.incr(frappe.cache.make_key(version_key))

	@classmethod
	def _dirty_events(cls) -> set[str]:
		dirty = getattr(frappe.local, "_booking_cache_dirty_events", None)
		if dirty is None:
			dirty = set()
			frappe.local._booking_cache_dirty_events = dirty
		return dirty

	@classmethod
	def _dirty_routes(cls) -> set[str]:
		dirty = getattr(frappe.local, "_booking_cache_dirty_routes", None)
		if dirty is None:
			dirty = set()
			frappe.local._booking_cache_dirty_routes = dirty
		return dirty

	@classmethod
	def _schedule_transaction_cleanup(cls) -> None:
		if getattr(frappe.local, "_booking_cache_cleanup_scheduled", False):
			return
		frappe.local._booking_cache_cleanup_scheduled = True
		frappe.db.after_commit.add(cls._flush_transaction_state)
		frappe.db.after_rollback.add(cls._flush_transaction_state)

	@classmethod
	def _flush_transaction_state(cls) -> None:
		dirty_events = list(cls._dirty_events())
		dirty_routes = list(cls._dirty_routes())
		cls._dirty_events().clear()
		cls._dirty_routes().clear()
		frappe.local._booking_cache_cleanup_scheduled = False
		for event_id in dirty_events:
			cls._bump_version(cls.metadata_version_key(event_id))
		for route in dirty_routes:
			cls._bump_version(cls.route_version_key(route))

	@classmethod
	def get_metadata(cls, event_id: str | int, loader: Callable[[str], dict]) -> dict:
		key_id = str(event_id)
		if frappe.flags.in_patch or key_id in cls._dirty_events():
			return loader(key_id)
		version = cls._read_version(cls.metadata_version_key(key_id))
		cache_key = cls.metadata_key(key_id, version)
		cached = frappe.cache.get_value(cache_key)
		if cached is not None:
			return cached
		data = loader(key_id)
		frappe.cache.set_value(cache_key, data, expires_in_sec=BOOKING_METADATA_TTL_SECONDS)
		return data

	@classmethod
	def get_event_id_by_route(cls, event_route: str) -> str | None:
		if not event_route:
			return None
		if frappe.flags.in_patch or event_route in cls._dirty_routes():
			name = frappe.db.get_value("Buzz Event", {"route": event_route}, "name")
			return str(name) if name else None
		version = cls._read_version(cls.route_version_key(event_route))
		cache_key = cls.route_key(event_route, version)
		cached = frappe.cache.get_value(cache_key)
		if cached is not None:
			return str(cached)
		name = frappe.db.get_value("Buzz Event", {"route": event_route}, "name")
		if not name:
			return None
		event_id = str(name)
		frappe.cache.set_value(cache_key, event_id, expires_in_sec=EVENT_ROUTE_TTL_SECONDS)
		return event_id

	@classmethod
	def invalidate_event(cls, event_id: str | int | None) -> None:
		if not event_id:
			return
		key_id = str(event_id)
		cls._dirty_events().add(key_id)
		cls._bump_version(cls.metadata_version_key(key_id))
		cls._schedule_transaction_cleanup()

	@classmethod
	def invalidate_route(cls, route: str | None) -> None:
		if not route:
			return
		cls._dirty_routes().add(route)
		cls._bump_version(cls.route_version_key(route))
		cls._schedule_transaction_cleanup()


def invalidate_event_booking_cache(event_id: str | int | None) -> None:
	EventBookingCache.invalidate_event(event_id)


def invalidate_for_event_child(doc, method=None, *args, **kwargs) -> None:
	before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	if doc.doctype == "Buzz Form":
		relevant_doctypes = set(APPLIED_TO_BY_FORM_DOCTYPE)
		before_type = before.get("form_doctype") if before else None
		if doc.get("form_doctype") not in relevant_doctypes and before_type not in relevant_doctypes:
			return
	event_ids = {doc.get("event")}
	if before:
		event_ids.add(before.get("event"))
	for event_id in event_ids:
		EventBookingCache.invalidate_event(event_id)


def invalidate_for_event(doc, method=None, *args, **kwargs) -> None:
	before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	EventBookingCache.invalidate_event(doc.name)
	routes = {doc.get("route")}
	if before:
		routes.add(before.get("route"))
	for route in routes:
		EventBookingCache.invalidate_route(route)
