import frappe
from frappe import _
from frappe.model.naming import append_number_if_name_exists
from frappe.query_builder import Case
from frappe.utils import getdate

from buzz.api.events.exceptions import (
	CannotCreateEvents,
	CannotManageEvent,
	EventNotFound,
	ZoomNotAvailable,
)
from buzz.api.events.schemas import (
	CreatedEvent,
	EventDetail,
	EventVenue,
	MyEvent,
	MyEventsResponse,
	NewEvent,
)
from buzz.permissions import has_team_access, my_teams
from buzz.utils import is_app_installed


def my_events() -> MyEventsResponse:
	upcoming, past = split_by_date(events_for(frappe.session.user))
	return MyEventsResponse(upcoming=upcoming, past=past)


def events_for(user: str) -> list[MyEvent]:
	"""Team membership and ticket ownership are the authorization here.

	Buzz Event's own query condition shows published events to everyone and drafts to the
	team, which is neither list: a Viewer needs their team's drafts, and an attendee needs
	the unpublished event they hold a ticket to.
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

	rows = (
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
			event.venue,
			event.banner_image,
			event.team,
			team.team_name,
			team.logo.as_("team_logo"),
			Case().when(hosted, 1).else_(0).as_("is_host"),
		)
		.where(hosted | ticketed)
		.orderby(event.start_date)
		.orderby(event.start_time)
	).run(as_dict=True)

	# Buzz Event autonames to integers, while every link to it travels as a string.
	return [MyEvent(**row | {"name": str(row.name)}) for row in rows]


def split_by_date(events: list[MyEvent]) -> tuple[list[MyEvent], list[MyEvent]]:
	upcoming, past = [], []
	for event in events:
		is_over = (event.end_date or event.start_date) < getdate()
		(past if is_over else upcoming).append(event)
	return upcoming, list(reversed(past))


DETAIL_FIELDS = (
	"name",
	"title",
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
