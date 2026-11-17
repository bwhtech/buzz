from typing import Literal

from frappe.mcp.tools import ToolArguments
from pydantic import Field

from buzz.api.booking import get_booking_details
from buzz.api.booking.my_bookings import my_bookings_page
from buzz.api.events import get_my_events
from buzz.api.proposals import get_my_proposals
from buzz.api.sponsorships import get_user_sponsorship_inquiries
from buzz.api.tickets import get_ticket_details
from buzz.mcp.tools import NoArguments, PageArguments, read_only_tool


class MyEventsArguments(PageArguments):
	when: Literal["upcoming", "past"] = "upcoming"
	role: Literal["hosting", "attending"] | None = None


class BookingArguments(ToolArguments):
	booking_id: str = Field(min_length=1)


class TicketArguments(ToolArguments):
	ticket_id: str = Field(min_length=1)


def list_my_events(when: str, role: str | None, start: int, limit: int) -> dict:
	events = getattr(get_my_events({"role": [role]} if role else None), when)
	return {"events": events[start : start + limit], "has_next_page": len(events) > start + limit}


LIST_MY_EVENTS = read_only_tool(
	name="list_my_events",
	description=(
		"One page of events the user hosts through their teams or holds a ticket to. "
		"Upcoming events come soonest first, past events most recent first."
	),
	arguments=MyEventsArguments,
	handler=list_my_events,
)

LIST_MY_BOOKINGS = read_only_tool(
	name="list_my_bookings",
	description="One page of the user's bookings with event title, start date and status, newest first.",
	arguments=PageArguments,
	handler=my_bookings_page,
)

GET_BOOKING = read_only_tool(
	name="get_booking",
	description=(
		"One booking with its tickets, add-ons and cancellation state. "
		"booking_id: a booking name from list_my_bookings."
	),
	arguments=BookingArguments,
	handler=get_booking_details,
)

GET_TICKET = read_only_tool(
	name="get_ticket",
	description=(
		"One ticket with its event, venue and add-ons. "
		"ticket_id: a ticket name from get_booking, or a guest name from list_event_guests."
	),
	arguments=TicketArguments,
	handler=get_ticket_details,
)

LIST_MY_PROPOSALS = read_only_tool(
	name="list_my_proposals",
	description="Talk proposals the user submitted or is listed on as a speaker.",
	arguments=NoArguments,
	handler=get_my_proposals,
)

LIST_MY_SPONSORSHIP_ENQUIRIES = read_only_tool(
	name="list_my_sponsorship_enquiries",
	description="Sponsorship enquiries the user made, with their tier and status.",
	arguments=NoArguments,
	handler=get_user_sponsorship_inquiries,
)

ATTENDEE_TOOLS = (
	LIST_MY_EVENTS,
	LIST_MY_BOOKINGS,
	GET_BOOKING,
	GET_TICKET,
	LIST_MY_PROPOSALS,
	LIST_MY_SPONSORSHIP_ENQUIRIES,
)
