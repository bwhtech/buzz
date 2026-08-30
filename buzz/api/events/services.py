import frappe
from frappe import _
from frappe.model.naming import append_number_if_name_exists
from frappe.query_builder import Case
from frappe.utils import getdate

from buzz.api.booking.services import are_registrations_closed
from buzz.api.events.exceptions import (
	CannotCreateEvents,
	CannotManageEvent,
	EventNotFound,
	ZoomNotAvailable,
)
from buzz.api.events.schemas import (
	CreatedEvent,
	EventDetail,
	EventGuest,
	EventGuestsResponse,
	EventVenue,
	GuestAddOn,
	MyEvent,
	MyEventFilters,
	MyEventsResponse,
	NewEvent,
	RouteAvailability,
)
from buzz.events.doctype.buzz_event.buzz_event import RESERVED_EVENT_ROUTES
from buzz.permissions import has_team_access, my_teams
from buzz.utils import is_app_installed


def my_events(filters: MyEventFilters | None = None) -> MyEventsResponse:
	upcoming, past = split_by_date(events_for(frappe.session.user, filters))
	return MyEventsResponse(upcoming=upcoming, past=past)


def events_for(user: str, filters: MyEventFilters | None = None) -> list[MyEvent]:
	"""Team membership and ticket ownership are the authorization here.

	Buzz Event's own query condition shows published events to everyone and drafts to the
	team, which is neither list: a Viewer needs their team's drafts, and an attendee needs
	the unpublished event they hold a ticket to.

	Filters only ever narrow. The hosted-or-ticketed predicate still bounds the result, so
	a team filter cannot reach an event the user could not already see, and needs no guard
	of its own.
	"""
	event = frappe.qb.DocType("Buzz Event")
	ticket = frappe.qb.DocType("Event Ticket")
	team = frappe.qb.DocType("Buzz Team")

	hosted = event.team.isin(my_teams(user))
	ticketed = event.name.isin(
		frappe.qb.from_(ticket)
		.select(ticket.event)
		.where((ticket.attendee_email == user) & (ticket.docstatus == 1))
	)

	query = (
		frappe.qb.from_(event)
		# Left join: an event predating the team backfill still belongs in the feed.
		.left_join(team)
		.on(team.name == event.team)
		.select(
			event.name,
			event.title,
			event.route,
			event.start_date,
			event.end_date,
			event.start_time,
			event.end_time,
			event.venue,
			event.medium,
			event.banner_image,
			event.team,
			team.team_name,
			team.logo.as_("team_logo"),
			Case().when(hosted, 1).else_(0).as_("is_host"),
			Case().when(ticketed, 1).else_(0).as_("is_attendee"),
		)
		.where(hosted | ticketed)
		.orderby(event.start_date)
		.orderby(event.start_time)
	)

	query = narrow(query, event, hosted, ticketed, filters)
	rows = query.run(as_dict=True)

	# Buzz Event autonames to integers, while every link to it travels as a string.
	return [MyEvent(**row | {"name": str(row.name)}) for row in rows]


def narrow(query, event, hosted, ticketed, filters: MyEventFilters | None):
	"""Each set field adds one clause; the role reuses the criterions built above."""
	if not filters:
		return query
	if filters.role:
		query = query.where(hosted if filters.role == "hosting" else ticketed)
	if filters.team:
		query = query.where(event.team == filters.team)
	if filters.medium:
		query = query.where(event.medium == filters.medium)
	return query


def split_by_date(events: list[MyEvent]) -> tuple[list[MyEvent], list[MyEvent]]:
	upcoming, past = [], []
	for event in events:
		is_over = (event.end_date or event.start_date) < getdate()
		(past if is_over else upcoming).append(event)
	return upcoming, list(reversed(past))


DETAIL_FIELDS = (
	"name",
	"title",
	"route",
	"team",
	"start_date",
	"end_date",
	"start_time",
	"end_time",
	"time_zone",
	"short_description",
	"about",
	"banner_image",
	"medium",
	"venue",
	"meeting_link",
	"is_published",
)


def event_detail(event: str) -> EventDetail:
	"""One event for its manage page, with the venue and meeting link resolved."""
	row = frappe.db.get_value("Buzz Event", event, DETAIL_FIELDS, as_dict=True)
	if not row:
		EventNotFound.throw()

	# Read is not enough: this payload backs the page that edits the event.
	if not has_team_access(row.team, "write", frappe.session.user):
		CannotManageEvent.throw()

	return EventDetail(
		**row | {"name": str(row.name), "venue": venue_of(row.venue), "meeting_link": meeting_link_of(row)}
	)


def venue_of(venue: str | None) -> EventVenue | None:
	if not venue:
		return None
	address = frappe.db.get_value("Event Venue", venue, "address")
	return EventVenue(name=venue, address=address)


def meeting_link_of(row) -> str | None:
	"""The organiser's own link, falling back to the one Zoom issued.

	`zoom_meeting` is a custom field the zoom_integration app adds, so it is absent on a
	site without it — and a booked meeting is the link even when nobody typed one in.
	"""
	if row.meeting_link:
		return row.meeting_link
	if not is_app_installed("zoom_integration"):
		return None

	meeting = frappe.db.get_value("Buzz Event", row.name, "zoom_meeting")
	return frappe.db.get_value("Zoom Meeting", meeting, "zoom_link") if meeting else None


def event_guests(event: str) -> EventGuestsResponse:
	"""Everyone holding a ticket to an event.

	A submitted ticket only — a draft belongs to a booking still being paid for. Read
	access is the bar: this shows the team what it already sees through the doctype.
	"""
	team = frappe.db.get_value("Buzz Event", event, "team")
	if not frappe.db.exists("Buzz Event", event):
		EventNotFound.throw()

	if not has_team_access(team, "read", frappe.session.user):
		CannotManageEvent.throw()

	tickets = frappe.get_all(
		"Event Ticket",
		filters={"event": event, "docstatus": 1},
		fields=["name", "attendee_name", "attendee_email", "ticket_type"],
		order_by="attendee_name asc",
	)

	by_ticket = add_ons_by_ticket([ticket.name for ticket in tickets])
	# Event Ticket Type is autonamed, so the link value is a number nobody recognises.
	type_titles = titles_of("Event Ticket Type", {ticket.ticket_type for ticket in tickets})

	guests = [
		EventGuest(
			**ticket | {"ticket_type": type_titles.get(ticket.ticket_type) or ticket.ticket_type},
			add_ons=by_ticket.get(ticket.name, []),
		)
		for ticket in tickets
	]
	doc = frappe.get_cached_doc("Buzz Event", event)
	return EventGuestsResponse(
		title=doc.title,
		total=len(guests),
		registrations_closed=are_registrations_closed(doc),
		guests=guests,
	)


def titles_of(doctype: str, names: set[str | None]) -> dict[str, str]:
	"""Name-to-title map for a set of links, in one query."""
	wanted = [name for name in names if name]
	if not wanted:
		return {}

	rows = frappe.get_all(doctype, filters={"name": ("in", wanted)}, fields=["name", "title"], as_list=True)
	# An autonamed doctype comes back with integer names, while every link to it travels
	# as a string — without this the map never matches.
	return {str(name): title for name, title in rows}


def add_ons_by_ticket(tickets: list[str]) -> dict[str, list[GuestAddOn]]:
	"""Add-ons for every ticket at once, rather than a query per row."""
	if not tickets:
		return {}

	# Query builder rather than get_all: a child doctype has no standalone permission of
	# its own, and the team check above is the authorization.
	value = frappe.qb.DocType("Ticket Add-on Value")
	rows = (
		frappe.qb.from_(value)
		.select(value.parent, value.add_on, value.value)
		.where((value.parenttype == "Event Ticket") & value.parent.isin(tickets))
	).run(as_dict=True)
	titles = titles_of("Ticket Add-on", {row.add_on for row in rows})

	by_ticket: dict[str, list[GuestAddOn]] = {}
	for row in rows:
		add_on = GuestAddOn(title=titles.get(row.add_on) or row.add_on, value=row.value)
		by_ticket.setdefault(row.parent, []).append(add_on)
	return by_ticket


def route_availability(route: str, event: str | None = None) -> RouteAvailability:
	"""Whether an event can take this route.

	Routes are the public URL namespace, so this checks every event rather than only the
	published ones: an unpublished event still holds its route, and publishing it later
	would collide.
	"""
	route = (route or "").strip().lower()
	if not route:
		return RouteAvailability(available=False, message=_("Enter a route."))

	if route in RESERVED_EVENT_ROUTES:
		return RouteAvailability(
			available=False, message=_("'{0}' is reserved and cannot be used.").format(route)
		)

	filters = {"route": route}
	if event:
		filters["name"] = ("!=", event)

	if frappe.db.exists("Buzz Event", filters):
		return RouteAvailability(available=False, message=_("This route is already taken."))

	return RouteAvailability(available=True, message=_("This route is available."))


# Buzz Event demands a category and a host, neither of which the create form asks for.
# These are the defaults it fills in; the organiser changes them on the event afterwards.
DEFAULT_CATEGORY = "Meetups"
# Zoom-backed, so the meeting the organiser asked for is the one the event gets.
ZOOM_CATEGORY = "Zoom Meeting"


def create_event(new: NewEvent) -> CreatedEvent:
	"""Create an event for a team from the dashboard's create form."""
	if not has_team_access(new.team, "create", frappe.session.user):
		CannotCreateEvents.throw()

	# Checked before the insert: a half-made event the organiser has to clean up is worse
	# than a refusal.
	if new.zoom_meeting and not is_app_installed("zoom_integration"):
		ZoomNotAvailable.throw()

	event = frappe.get_doc(
		{
			"doctype": "Buzz Event",
			"team": new.team,
			"title": new.title,
			"start_date": new.start_date,
			"end_date": new.end_date,
			"start_time": new.start_time,
			"end_time": new.end_time,
			"about": new.about,
			"banner_image": new.banner_image,
			"time_zone": new.time_zone,
			"venue": new.venue,
			"medium": "Online" if new.zoom_meeting else "In Person",
			"category": ZOOM_CATEGORY if new.zoom_meeting else DEFAULT_CATEGORY,
			"host": host_for(new.team),
		}
	).insert()

	if new.zoom_meeting:
		book_zoom_meeting(event)

	return CreatedEvent(name=str(event.name), title=event.title)


def book_zoom_meeting(event) -> None:
	"""Book the Zoom meeting the organiser asked for, and keep the event either way.

	`create_meeting_on_zoom` calls Zoom during the request and writes the meeting back
	onto the event. Letting it raise would roll the insert back with it, so a Zoom outage
	would cost the organiser the whole event rather than just the meeting; they can add
	one from the event afterwards.
	"""
	try:
		event.create_meeting_on_zoom()
	except Exception:
		frappe.log_error(title="Zoom meeting not created", reference_doctype="Buzz Event")
		frappe.msgprint(
			_("The event was created, but its Zoom meeting could not be. Add one from the event."),
			title=_("Zoom Meeting Not Created"),
			indicator="orange",
		)


def host_for(team: str) -> str:
	"""The team's own Event Host, made on first use.

	Event Host is required on every event but absent from the create form, and a new team
	has none. Host names are docnames and therefore global, so an existing name is given a
	suffix rather than joined.
	"""
	existing = frappe.db.get_value("Event Host", {"team": team}, "name")
	if existing:
		return existing

	team_name = frappe.db.get_value("Buzz Team", team, "team_name") or team
	host = frappe.get_doc({"doctype": "Event Host", "name": team_name, "team": team})
	host.name = append_number_if_name_exists("Event Host", team_name)
	# Event Host is readable by the team but writable by Event Manager only, and creating
	# an event is what mints it — the team check above is the authorisation.
	host.insert(ignore_permissions=True)
	return host.name
