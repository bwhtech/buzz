import frappe
from frappe.integrations.utils import make_post_request
from frappe.utils import getdate, today

from buzz.api.events.services import primary_host_of
from buzz.www.event.meta import EventMeta

API_PATH = "/api/v2/method/buzz.api.listings"


def listing_enabled() -> bool:
	return bool(frappe.db.get_single_value("Buzz Settings", "list_on_buzz_events"))


def source_id_of(event_name: str) -> str:
	return f"{frappe.local.site}:{event_name}"


class ListingPush:
	"""Lists one event on the partner's community page on buzz.events, or takes it off."""

	def __init__(self, event):
		self.event = event
		self.source_id = source_id_of(event.name)

	def sync_listing(self) -> None:
		if self.event.is_published and not self.has_ended():
			post_to_buzz_events("upsert_event", {"event": self.payload()})
		else:
			post_to_buzz_events("remove_event", {"source_id": self.source_id})

	def has_ended(self) -> bool:
		return getdate(self.event.end_date or self.event.start_date) < getdate(today())

	def host_label(self) -> str:
		host = primary_host_of(self.event.team)
		return host.label if host else frappe.local.site

	def payload(self) -> dict:
		meta = EventMeta(self.event, {})
		return {
			"source_id": self.source_id,
			"event_title": self.event.title,
			"host": self.host_label(),
			"event_location": self.event.get_venue_name() or "Online",
			"start_datetime": meta.event_datetime(self.event.start_date, self.event.start_time),
			"end_datetime": meta.end_datetime(),
			"event_url": meta.url(),
		}


def post_to_buzz_events(method: str, body: dict) -> None:
	settings = frappe.get_cached_doc("Buzz Settings")
	token = f"{settings.buzz_events_api_key}:{settings.get_password('buzz_events_api_secret')}"
	make_post_request(
		f"{settings.buzz_events_url.rstrip('/')}{API_PATH}.{method}",
		headers={"Authorization": f"token {token}"},
		json=body,
		timeout=30,
	)


def push_event(event_name: str) -> None:
	if listing_enabled() and frappe.db.exists("Buzz Event", event_name):
		ListingPush(frappe.get_doc("Buzz Event", event_name)).sync_listing()


def remove_listing(source_id: str) -> None:
	if listing_enabled():
		post_to_buzz_events("remove_event", {"source_id": source_id})


def sync_all_events() -> None:
	# A one-day event may leave end_date empty.
	upcoming_filters = {"end_date": [">=", today()], "start_date": [">=", today()]}
	event_names = frappe.get_all("Buzz Event", {"is_published": 1}, or_filters=upcoming_filters, pluck="name")
	for event_name in event_names:
		try:
			push_event(event_name)
		except Exception:
			frappe.log_error(title=f"buzz.events listing failed for event {event_name}")


def enqueue_push(event, method=None) -> None:
	# An event that never went live has no listing to update or take down.
	never_published = not event.is_published and not event.has_value_changed("is_published")
	if never_published or not listing_enabled():
		return
	frappe.enqueue(
		"buzz.events.buzz_events_listing.push_event",
		event_name=str(event.name),
		job_id=f"buzz_events_listing_{event.name}",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def enqueue_remove(event, method=None) -> None:
	if event.is_published and listing_enabled():
		frappe.enqueue(
			"buzz.events.buzz_events_listing.remove_listing",
			source_id=source_id_of(str(event.name)),
			enqueue_after_commit=True,
		)
