from frappe.mcp.tools import DocumentName, ToolArguments
from pydantic import Field

from buzz.api.events import (
	get_event,
	get_event_guests,
	get_event_registration_trend,
	get_event_ticket_types,
)
from buzz.api.proposals import get_event_proposals
from buzz.api.teams import get_my_teams, get_team_overview
from buzz.api.tickets.exceptions import TicketNotFound
from buzz.api.transactions import get_transaction_summary
from buzz.mcp.tools import NoArguments, PageArguments, read_only_tool

# Contact details stay out of bulk lists; get_guest returns them for one guest at a time.
# No search tool: event search shows guest emails.
CONTACT_FIELDS = ("attendee_email",)


class EventArguments(ToolArguments):
	event: DocumentName


class EventPageArguments(EventArguments, PageArguments):
	search: str | None = None


class GuestArguments(EventArguments):
	guest: str = Field(min_length=1)


class TrendArguments(EventArguments):
	days: int = Field(default=14, ge=2, le=90)


class TeamArguments(ToolArguments):
	team: str = Field(min_length=1)


def list_event_guests(event: str, search: str | None, start: int, limit: int) -> dict:
	page = get_event_guests(event, search=search, start=start, limit=limit).__json__()
	for guest in page["guests"]:
		for field in CONTACT_FIELDS:
			guest.pop(field, None)
	return page


def list_event_proposals(event: str, search: str | None, start: int, limit: int) -> dict:
	page = get_event_proposals(event, search=search, start=start, limit=limit).__json__()
	for proposal in page["proposals"]:
		for speaker in proposal["speakers"]:
			speaker.pop("email", None)
	return page


def get_guest(event: str, guest: str) -> dict:
	guests = get_event_guests(event, name=guest).guests
	if not guests:
		TicketNotFound.throw()
	return guests[0].__json__()


GET_EVENT = read_only_tool(
	name="get_event",
	description="One event's details for its organizers. event: the event name from list_my_events.",
	arguments=EventArguments,
	handler=get_event,
)

LIST_EVENT_GUESTS = read_only_tool(
	name="list_event_guests",
	description=(
		"One page of an event's guests with ticket type and check-in state, newest first, without "
		"contact details. event: the event name from list_my_events; search matches name, email or ticket."
	),
	arguments=EventPageArguments,
	handler=list_event_guests,
)

GET_GUEST = read_only_tool(
	name="get_guest",
	description=(
		"One guest of an event, including their email. "
		"event: the event name from list_my_events; guest: a guest name from list_event_guests."
	),
	arguments=GuestArguments,
	handler=get_guest,
)

GET_REGISTRATION_TREND = read_only_tool(
	name="get_registration_trend",
	description=(
		"Registrations per day and ticket type over the last `days` days. "
		"event: the event name from list_my_events."
	),
	arguments=TrendArguments,
	handler=get_event_registration_trend,
)

LIST_TICKET_TYPES = read_only_tool(
	name="list_ticket_types",
	description=(
		"An event's ticket types, add-ons, revenue and registration settings. "
		"event: the event name from list_my_events."
	),
	arguments=EventArguments,
	handler=get_event_ticket_types,
)

GET_SALES_SUMMARY = read_only_tool(
	name="get_sales_summary",
	description=(
		"Revenue per currency, per payment method and per day for an event. "
		"event: the event name from list_my_events."
	),
	arguments=EventArguments,
	handler=get_transaction_summary,
)

LIST_EVENT_PROPOSALS = read_only_tool(
	name="list_event_proposals",
	description=(
		"One page of the talk proposals submitted to an event, newest first. "
		"event: the event name from list_my_events; search matches title or speaker."
	),
	arguments=EventPageArguments,
	handler=list_event_proposals,
)

LIST_MY_TEAMS = read_only_tool(
	name="list_my_teams",
	description="Teams the user belongs to, with their role in each.",
	arguments=NoArguments,
	handler=get_my_teams,
)

GET_TEAM_OVERVIEW = read_only_tool(
	name="get_team_overview",
	description="A team's profile, members, pending invites and tax details. team: the team name from list_my_teams.",
	arguments=TeamArguments,
	handler=get_team_overview,
)

ORGANIZER_TOOLS = (
	GET_EVENT,
	LIST_EVENT_GUESTS,
	GET_GUEST,
	GET_REGISTRATION_TREND,
	LIST_TICKET_TYPES,
	GET_SALES_SUMMARY,
	LIST_EVENT_PROPOSALS,
	LIST_MY_TEAMS,
	GET_TEAM_OVERVIEW,
)
