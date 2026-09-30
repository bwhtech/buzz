import frappe

from buzz.api.booking.schemas import MyBooking
from buzz.events.doctype.event_venue.event_venue import set_venue_names

MY_BOOKING_FIELDS = [
	"name",
	"event",
	"event.title as event_title",
	"event.start_date",
	"event.venue as venue",
	"docstatus",
	"total_amount",
	"currency",
	"creation",
	"status",
	{"attendees": ["ticket_type"]},
]
# The list has no paging; this is the page the dashboard showed before it moved here.
MY_BOOKINGS_LIMIT = 20


def my_bookings() -> list[MyBooking]:
	"""The session user's submitted and cancelled bookings, newest first."""
	rows = frappe.get_list(
		"Event Booking",
		fields=MY_BOOKING_FIELDS,
		filters={"user": frappe.session.user, "docstatus": ["!=", 0]},
		order_by="creation desc",
		limit=MY_BOOKINGS_LIMIT,
	)
	set_venue_names(rows)
	return [MyBooking(**row) for row in rows]
