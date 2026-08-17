import frappe
from frappe.query_builder import Case
from frappe.utils import getdate

from buzz.api.events.schemas import MyEvent, MyEventsResponse
from buzz.permissions import my_teams


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
