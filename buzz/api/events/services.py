from datetime import datetime

import frappe
from frappe import _
from frappe.query_builder import Case, Criterion
from frappe.query_builder.functions import Count, Date
from frappe.utils import add_days, getdate

from buzz.api.booking.guests import email_otp_available, phone_otp_available
from buzz.api.booking.services import OFFLINE_PAYMENT_METHOD, are_registrations_closed
from buzz.api.events.exceptions import (
	CannotCreateEvents,
	CannotManageEvent,
	EventNotFound,
	ZoomNotAvailable,
)
from buzz.api.events.guest_zones import GuestZones
from buzz.api.events.schemas import (
	CreatedEvent,
	DailyRegistrations,
	EventDetail,
	EventExternalLink,
	EventGuest,
	EventGuestsResponse,
	EventHostRef,
	GuestAddOn,
	GuestAnswer,
	GuestTicketType,
	MyEvent,
	MyEventFilters,
	MyEventsResponse,
	NewEvent,
	RegistrationState,
	RegistrationTrend,
	RouteAvailability,
	TicketTypeTotal,
	VerificationMethods,
)
from buzz.api.filters.conditions import (
	ListConditions,
	filter_field,
	form_questions_by_doctype,
	question_fields,
)
from buzz.api.filters.schemas import FilterField
from buzz.events.countdown import event_countdown
from buzz.events.doctype.buzz_event.buzz_event import RESERVED_EVENT_ROUTES, BuzzEvent
from buzz.events.doctype.buzz_form.form_types import (
	ATTENDEE_FORM_DOCTYPE,
	REGISTRATION_FORM_DOCTYPE,
	event_form,
)
from buzz.events.doctype.buzz_team.buzz_team import personal_team_owner
from buzz.events.doctype.event_venue.details import venue_details
from buzz.permissions import (
	event_section_permissions,
	events_with_section_access,
	get_section_access,
	has_section_permission,
	has_team_access,
)
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
	venue = frappe.qb.DocType("Event Venue")

	hosted = event.name.isin(event_names(events_with_section_access(user, "details")))
	ticketed = event.name.isin(
		event_names(
			frappe.qb.from_(ticket)
			.select(ticket.event)
			.where((ticket.attendee_email == user) & (ticket.docstatus == 1))
		)
		+ event_names(events_booked_by(user))
	)

	query = (
		frappe.qb.from_(event)
		# Left join: an event predating the team backfill still belongs in the feed.
		.left_join(team)
		.on(team.name == event.team)
		.left_join(venue)
		.on(venue.name == event.venue)
		.select(
			event.name,
			event.title,
			event.route,
			event.start_date,
			event.end_date,
			event.start_time,
			event.end_time,
			venue.venue_name.as_("venue"),
			event.medium,
			event.banner_image,
			event.is_published,
			event.team,
			team.team_name,
			team.logo.as_("team_logo"),
			Case().when(hosted, 1).else_(0).as_("is_host"),
			Case().when(ticketed, 1).else_(0).as_("is_attendee"),
		)
		.where(hosted | ticketed)
		# Undated events trail the dated ones they are upcoming with
		.orderby(event.start_date.isnull())
		.orderby(event.start_date)
		.orderby(event.start_time)
	)

	query = narrow(query, event, hosted, ticketed, filters)
	rows = query.run(as_dict=True)

	# Buzz Event autonames to integers, while every link to it travels as a string.
	return [MyEvent(**row | {"name": str(row.name)}) for row in rows]


def event_names(query) -> list:
	"""Run up front: Buzz Event names are integers while links to them are varchar, so as an
	IN subquery MariaDB re-scans the linked table once per event row. NULL keeps IN valid
	when nothing matches."""
	return query.distinct().run(pluck=True) or [None]


def events_booked_by(user: str):
	"""A booking that holds no ticket of the user's still belongs in their feed: one bought for
	others, one cancelled or rejected, an offline payment still awaiting approval, or a
	registration request (a draft until the organizer decides)."""
	booking = frappe.qb.DocType("Event Booking")
	awaiting_approval = (booking.status == "Approval Pending") & (
		booking.payment_method == OFFLINE_PAYMENT_METHOD
	)
	is_request = booking.request_type.isin(["Approval", "Waitlist"])
	return (
		frappe.qb.from_(booking)
		.select(booking.event)
		.where((booking.user == user) & ((booking.docstatus != 0) | awaiting_approval | is_request))
	)


def narrow(query, event, hosted, ticketed, filters: MyEventFilters | None):
	"""Each set field adds one clause; the role reuses the criterions built above."""
	filters = filters or MyEventFilters()
	if not filters.include_archived:
		query = query.where(event.is_published == 1)
	if filters.role:
		roles = {"hosting": hosted, "attending": ticketed}
		query = query.where(Criterion.any([roles[role] for role in filters.role]))
	if filters.team:
		query = query.where(event.team.isin(filters.team))
	if filters.medium:
		query = query.where(event.medium.isin(filters.medium))
	if search := (filters.search or "").strip():
		# Typed % and _ are matched as themselves, not as wildcards.
		escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
		query = query.where(event.title.like(f"%{escaped}%"))
	return query


def split_by_date(events: list[MyEvent]) -> tuple[list[MyEvent], list[MyEvent]]:
	upcoming, past = [], []
	for event in events:
		is_over = bool(event.start_date) and (event.end_date or event.start_date) < getdate()
		(past if is_over else upcoming).append(event)
	return upcoming, list(reversed(past))


DETAIL_FIELDS = (
	"name",
	"title",
	"route",
	"team",
	"modified",
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
	"show_countdown",
)


def get_event_doc(event: str) -> BuzzEvent:
	try:
		return frappe.get_cached_doc("Buzz Event", str(event))
	except frappe.DoesNotExistError:
		frappe.clear_last_message()
		EventNotFound.throw()


def event_detail(event: str) -> EventDetail:
	"""One event for its manage page, with the venue and meeting link resolved."""
	doc = get_event_doc(event)
	perms = event_section_permissions(event, "details", team=doc.team or "")
	if not perms["can_read"]:
		CannotManageEvent.throw()

	row = frappe._dict({field: doc.get(field) for field in DETAIL_FIELDS})
	return EventDetail(
		**row
		| {
			"name": str(doc.name),
			"venue": venue_details(doc.venue),
			"meeting_link": meeting_link_of(doc),
			"primary_host": primary_host_of(doc.team),
			"co_hosts": co_hosts_of(event) if doc.co_hosts else [],
			"external_links": [
				EventExternalLink(icon=link.icon, label=link.label, url=link.url)
				for link in doc.external_links
			],
			"topics": [topic.topic for topic in doc.topics],
			"countdown": event_countdown(doc),
			# Details View opens the same page with its fields locked.
			"can_write": perms["can_write"],
		}
	)


def primary_host_of(team: str | None) -> EventHostRef | None:
	"""The team hosting the event."""
	if not team:
		return None
	row = frappe.get_cached_value("Buzz Team", team, ["team_name", "logo", "is_personal"], as_dict=True)
	owner = personal_team_owner(team) if row and row.is_personal else None
	if owner:
		return EventHostRef(host=team, label=owner.full_name, logo=owner.user_image)
	return EventHostRef(host=team, label=row.team_name or team, logo=row.logo) if row else None


def co_hosts_of(event: str) -> list[EventHostRef]:
	"""Co-hosts in table order.

	Read as SQL rather than through `get_list`: `Event Host` is filtered to the reader's
	own teams, and a co-host may belong to another.
	"""
	co_host, host = frappe.qb.DocType("Event CoHost"), frappe.qb.DocType("Event Host")
	rows = (
		frappe.qb.from_(co_host)
		.join(host)
		.on(host.name == co_host.host)
		.select(host.name, host.host_name, host.logo)
		.where((co_host.parenttype == "Buzz Event") & (co_host.parent == str(event)))
		.orderby(co_host.idx)
	).run(as_dict=True)
	return [EventHostRef(host=row.name, label=row.host_name or row.name, logo=row.logo) for row in rows]


def create_co_host(
	event: str,
	host_name: str,
	logo: str | None = None,
	by_line: str | None = None,
	about: str | None = None,
) -> EventHostRef:
	"""Add an organisation with no team here as a co-host of the event.

	The team's own host of that name is reused rather than minted twice: names are no
	longer docnames, so a second record would list the same organisation twice.
	"""
	doc = manageable_event(event)
	existing = frappe.db.get_value("Event Host", {"host_name": host_name, "team": doc.team}, "name")
	if existing:
		host = frappe.get_doc("Event Host", existing)
	else:
		host = frappe.get_doc(
			{
				"doctype": "Event Host",
				"host_name": host_name,
				"team": doc.team,
				"logo": logo,
				"by_line": by_line,
				"about": about,
			}
		)
		# Event Host is Event Manager-writable; the team access check above is the authorisation.
		host.insert(ignore_permissions=True)

	doc.append("co_hosts", {"host": host.name})
	doc.save()
	return EventHostRef(host=host.name, label=host.host_name, logo=host.logo)


def remove_co_host(event: str, host: str) -> None:
	"""Drop a co-host from the event. The Event Host record itself is left alone."""
	doc = manageable_event(event)
	doc.co_hosts = [row for row in doc.co_hosts if row.host != host]
	doc.save()


def manageable_event(event: str, section: str = "details") -> BuzzEvent:
	doc = frappe.get_doc("Buzz Event", event)
	if not has_section_permission(event, section, "write", frappe.session.user):
		CannotManageEvent.throw()
	return doc


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


GUESTS_PAGE_SIZE = 20


def guest_search_filters(search: str | None) -> list[list] | None:
	"""Name, email or ticket ID, matched loosely."""
	term = (search or "").strip()
	if not term:
		return None

	return [
		["attendee_name", "like", f"%{term}%"],
		["attendee_email", "like", f"%{term}%"],
		["name", "like", f"%{term}%"],
	]


def registration_link(doc) -> str | None:
	"""An event that sends people elsewhere is managed elsewhere: link where they land."""
	if doc.external_registration_page:
		return doc.registration_url
	return f"/b/register/{doc.route}" if doc.route else None


def set_registration_state(event: str, closed: bool) -> RegistrationState:
	"""Answer with the state the server ends up in: opening cannot beat the event's end date."""
	doc = manageable_event(event, "ticketing")
	# Without a registration form an event takes no registrations, which is already closed.
	if form := event_form(doc.name, REGISTRATION_FORM_DOCTYPE):
		form.flags.ignore_permissions = True
		form.set_closed(closed)
	return RegistrationState(registrations_closed=are_registrations_closed(doc))


def archive_event(event: str) -> None:
	"""Take the event and its forms off the public site."""
	manageable_event(event).archive_event()


def verification_methods() -> VerificationMethods:
	"""Site configuration, not event data: what a guest OTP could actually be sent over."""
	return VerificationMethods(email=email_otp_available(), phone=phone_otp_available())


def ensure_event_team_access(event: str, section: str | None) -> BuzzEvent:
	"""Read access to the event's section is the bar for everything a manage page shows.

	`section` None is team-level data, which a collaborator never reaches.
	"""
	doc = get_event_doc(event)
	user = frappe.session.user
	allowed = (
		has_section_permission(event, section, "read", user, team=doc.team or "")
		if section
		else has_team_access(doc.team, "read", user)
	)
	if not allowed:
		CannotManageEvent.throw()
	return doc


def event_guests(
	event: str,
	search: str | None = None,
	filters: str | None = None,
	order: str = "desc",
	start: int = 0,
	limit: int = GUESTS_PAGE_SIZE,
	checked_in: str | None = None,
	zone: str | None = None,
	name: str | None = None,
) -> EventGuestsResponse:
	"""One page of the people holding a ticket to an event.

	A submitted ticket only — a draft belongs to a booking still being paid for. Read
	access is the bar: this shows the team what it already sees through the doctype.

	Ordered by when the ticket was registered, newest first by default, so a page is a
	stable slice as the caller walks down the list. `checked_in` is "1" or "0" to keep only
	the guests who have, or have not, checked in today, at `zone` or the default zone.
	A `zone` also keeps only the tickets it lets in.
	"""
	doc = ensure_event_team_access(event, "guests")
	event_id = str(doc.name)

	counts_by_type = registrations_by_type(event_id)
	total = sum(counts_by_type.values())
	ticket_types = ticket_types_of(event_id)
	filter_fields, answer_parents = guest_filter_fields(event_id, ticket_types=ticket_types)
	ticket_table = frappe.qb.DocType("Event Ticket")
	extra_criteria = ListConditions(
		"Event Ticket", filter_fields, answer_parents, event=event_id
	).qb_criteria(filters, ticket_table)
	guest_zones = GuestZones(event_id, load_counts=total > 0)
	active_zone = guest_zones.resolve_zone(zone)
	if zone and (types := guest_zones.ticket_types.get(zone)):
		extra_criteria.append(ticket_table.ticket_type.isin(list(types)))
	if checked_in in ("0", "1"):
		extra_criteria.append(guest_zones.checked_in_criterion(active_zone, ticket_table, checked_in == "1"))
	if name:
		extra_criteria.append(ticket_table.name == name)
	if term := (search or "").strip():
		pattern = f"%{term}%"
		extra_criteria.append(
			ticket_table.attendee_name.like(pattern)
			| ticket_table.attendee_email.like(pattern)
			| ticket_table.name.like(pattern)
		)
	limit = max(1, min(int(limit), 100))
	start = max(0, int(start))
	order_dir = frappe.qb.asc if str(order).lower() == "asc" else frappe.qb.desc

	if not total:
		tickets = []
		matched = 0
	else:
		where_criterion = Criterion.all(
			[ticket_table.event == event_id, ticket_table.docstatus == 1, *extra_criteria]
		)
		tickets = (
			frappe.qb.from_(ticket_table)
			.select(
				ticket_table.name,
				ticket_table.attendee_name,
				ticket_table.attendee_email,
				ticket_table.ticket_type,
				ticket_table.booking,
				ticket_table.creation,
			)
			.where(where_criterion)
			.orderby(ticket_table.creation, order=order_dir)
			.orderby(ticket_table.name, order=order_dir)
			.limit(limit)
			.offset(start)
		).run(as_dict=True)
		if not extra_criteria:
			matched = total
		elif start == 0 and len(tickets) < limit:
			matched = len(tickets)
		else:
			count_rows = (
				frappe.qb.from_(ticket_table).select(Count(ticket_table.name)).where(where_criterion).run()
			)
			matched = count_rows[0][0] if count_rows else 0

	ticket_names = [ticket.name for ticket in tickets]
	booking_names = list({ticket.booking for ticket in tickets if ticket.booking})
	guest_zones.load_page_arrivals(ticket_names)
	active_arrivals = guest_zones.page_arrivals[active_zone]
	by_ticket = add_ons_by_ticket(ticket_names)
	ticket_answers, booking_answers = guest_answers_by_parent(ticket_names, booking_names)
	type_titles = {row.name: row.title for row in ticket_types}

	for ticket in tickets:
		ticket["zones"] = guest_zones.statuses(ticket.name, ticket.ticket_type)
		# The response names it registered_at, and the model forbids a field it does not declare.
		ticket["registered_at"] = ticket.pop("creation")
		ticket["ticket_type"] = type_titles.get(str(ticket.ticket_type)) or ticket.ticket_type

	guests = [
		EventGuest(
			**ticket,
			add_ons=by_ticket.get(ticket.name, []),
			checked_in_at=active_arrivals.get(ticket.name),
			answers=ticket_answers.get(ticket.name, []) + booking_answers.get(ticket.booking, []),
		)
		for ticket in tickets
	]
	return EventGuestsResponse(
		title=doc.title,
		start_date=doc.start_date,
		start_time=doc.start_time,
		end_date=doc.end_date,
		venue=doc.get_venue_name(),
		route=doc.route if doc.is_published else None,
		total=total,
		matched=matched,
		checked_in=guest_zones.checked_in_count(active_zone),
		checked_in_any_zone=guest_zones.checked_in_any_zone(),
		guests=guests,
		has_next_page=start + len(guests) < matched,
		filter_fields=filter_fields,
		zones=guest_zones.options(counts_by_type),
	)


def guest_filter_fields(
	event: str, ticket_types: list[GuestTicketType] | None = None
) -> tuple[list[FilterField], dict]:
	"""Ticket type, then the event's ticket and booking questions.

	Booking questions are answered once per booking, so they filter a ticket through the
	booking it belongs to. A fieldname asked on both keeps the ticket question.
	"""
	rows = ticket_types if ticket_types is not None else ticket_types_of(event)
	ticket_type_options = [(row.name, row.title) for row in rows]
	by_doctype = form_questions_by_doctype(event, (REGISTRATION_FORM_DOCTYPE, ATTENDEE_FORM_DOCTYPE))
	questions = {row.fieldname: row for row in by_doctype[REGISTRATION_FORM_DOCTYPE]}
	answer_parents = {fieldname: ("Event Booking", "booking") for fieldname in questions}
	for row in by_doctype[ATTENDEE_FORM_DOCTYPE]:
		questions[row.fieldname] = row
		answer_parents.pop(row.fieldname, None)
	fields = [
		filter_field("ticket_type", _("Ticket type"), "Link", ticket_type_options),
		*question_fields(questions.values()),
	]
	return fields, answer_parents


TREND_DAYS = 14


def registration_trend(event: str, days: int = TREND_DAYS) -> RegistrationTrend:
	"""Tickets raised per day and ticket type, oldest day first.

	Every day of the window against every type the event sells, zero-filled: the series
	is read as a shape, and a missing row would draw as a shorter week or a band that
	disappears mid-stack rather than a quiet one.
	"""
	ensure_event_team_access(event, "guests")

	days = max(2, min(int(days), 90))
	window = [add_days(getdate(), -offset) for offset in reversed(range(days))]
	counted = registrations_by_day_and_type(event, window[0])
	titles = {ticket_type.name: ticket_type.title for ticket_type in ticket_types_of(event)}

	all_time = registrations_by_type(event)

	return RegistrationTrend(
		total=sum(all_time.values()),
		by_ticket_type=[
			TicketTypeTotal(ticket_type=title or ticket_type, count=all_time.get(ticket_type, 0))
			for ticket_type, title in titles.items()
		],
		per_day=[
			DailyRegistrations(
				date=day,
				ticket_type=titles.get(ticket_type) or ticket_type,
				count=counted.get((day, ticket_type), 0),
			)
			for day in window
			for ticket_type in titles
		],
	)


def registrations_by_type(event: str) -> dict[str, int]:
	"""Counts per ticket type over the event's whole life, in one grouped query.

	Unwindowed on purpose: the donut sits beside the all-time total, and a fortnight's
	slice of an older event would read as the breakdown of a number it does not add up to.
	"""
	ticket = frappe.qb.DocType("Event Ticket")
	rows = (
		frappe.qb.from_(ticket)
		.select(ticket.ticket_type, Count("*").as_("count"))
		.where((ticket.event == event) & (ticket.docstatus == 1))
		.groupby(ticket.ticket_type)
	).run(as_dict=True)
	return {str(row.ticket_type): row.count for row in rows}


def registrations_by_day_and_type(event: str, since) -> dict[tuple, int]:
	"""Counts keyed by day and ticket type, in one grouped query.

	Query builder rather than get_all: grouping by the date part of a timestamp is a SQL
	function, which get_all takes only as a dict of the whole select.
	"""
	ticket = frappe.qb.DocType("Event Ticket")
	day = Date(ticket.creation)
	rows = (
		frappe.qb.from_(ticket)
		.select(day.as_("day"), ticket.ticket_type, Count("*").as_("count"))
		.where((ticket.event == event) & (ticket.docstatus == 1) & (ticket.creation >= since))
		.groupby(day, ticket.ticket_type)
	).run(as_dict=True)
	# Event Ticket Type is autonamed, so its link value arrives as a string either way.
	return {(getdate(row.day), str(row.ticket_type)): row.count for row in rows}


def ticket_types_of(event: str) -> list[GuestTicketType]:
	"""Every type the event sells, so the filter can offer one that nobody bought yet."""
	tt = frappe.qb.DocType("Event Ticket Type")
	rows = (
		frappe.qb.from_(tt).select(tt.name, tt.title).where(tt.event == str(event)).orderby(tt.title)
	).run(as_dict=True)
	# Autonamed, so the name arrives as an integer while every link to it travels as a string.
	return [GuestTicketType(name=str(row.name), title=row.title) for row in rows]


def titles_of(doctype: str, names: set[str | None]) -> dict[str, str]:
	"""Name-to-title map for a set of links, in one query."""
	wanted = [name for name in names if name]
	if not wanted:
		return {}

	rows = frappe.get_all(doctype, filters={"name": ("in", wanted)}, fields=["name", "title"], as_list=True)
	# An autonamed doctype comes back with integer names, while every link to it travels
	# as a string — without this the map never matches.
	return {str(name): title for name, title in rows}


def guest_answers_by_parent(
	tickets: list[str], bookings: list[str]
) -> tuple[dict[str, list[GuestAnswer]], dict[str, list[GuestAnswer]]]:
	"""Ticket and booking answers for one page of guests, in a single query."""
	if not tickets and not bookings:
		return {}, {}
	field = frappe.qb.DocType("Additional Field")
	branches = []
	if tickets:
		branches.append((field.parenttype == "Event Ticket") & field.parent.isin(tickets))
	if bookings:
		branches.append((field.parenttype == "Event Booking") & field.parent.isin(bookings))
	rows = (
		frappe.qb.from_(field)
		.select(field.parenttype, field.parent, field.label, field.fieldname, field.value)
		.where(Criterion.any(branches) & (field.value != ""))
		.orderby(field.idx)
	).run(as_dict=True)
	by_ticket: dict[str, list[GuestAnswer]] = {}
	by_booking: dict[str, list[GuestAnswer]] = {}
	for row in rows:
		target = by_ticket if row.parenttype == "Event Ticket" else by_booking
		target.setdefault(row.parent, []).append(
			GuestAnswer(label=row.label or row.fieldname, value=row.value)
		)
	return by_ticket, by_booking


def add_ons_by_ticket(tickets: list[str], parenttype: str = "Event Ticket") -> dict[str, list[GuestAddOn]]:
	"""Add-ons for every ticket at once, rather than a query per row."""
	if not tickets:
		return {}

	# Query builder rather than get_all: a child doctype has no standalone permission of
	# its own, and the team check above is the authorization.
	value = frappe.qb.DocType("Ticket Add-on Value")
	addon = frappe.qb.DocType("Ticket Add-on")
	rows = (
		frappe.qb.from_(value)
		.left_join(addon)
		.on(addon.name == value.add_on)
		.select(value.parent, value.add_on, addon.title.as_("add_on_title"), value.value)
		.where((value.parenttype == parenttype) & value.parent.isin(tickets))
	).run(as_dict=True)

	by_ticket: dict[str, list[GuestAddOn]] = {}
	for row in rows:
		add_on = GuestAddOn(title=row.add_on_title or row.add_on, value=row.value)
		by_ticket.setdefault(row.parent, []).append(add_on)
	return by_ticket


def route_availability(route: str, event: str | None = None) -> RouteAvailability:
	"""Whether an event can take this route.

	Routes are the public URL namespace, so this checks every event rather than only the
	published ones: an unpublished event still holds its route, and publishing it later
	would collide.
	"""
	route = (route or "").strip().lower()
	filters = {"route": route}
	if event:
		filters["name"] = ("!=", event)

	# A reserved route and a blank one are both unavailable, and the field says so the
	# same way a claimed one does — the reason is not the organiser's problem to fix.
	taken = not route or route in RESERVED_EVENT_ROUTES or frappe.db.exists("Buzz Event", filters)
	if taken:
		return RouteAvailability(available=False, message=_("Already exists"))

	return RouteAvailability(available=True, message=_("Available"))


# Buzz Event demands a category, which the create form does not ask for. This is the default
# it fills in; the organiser changes it on the event afterwards.
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
		}
	).insert()

	# Zoom needs a time slot; an unscheduled event books its meeting from the event later
	if new.zoom_meeting and event.has_schedule():
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
