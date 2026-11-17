import frappe
from frappe.query_builder import Order

from buzz.api.booking.schemas import MyBooking, MyBookingsPage
from buzz.permissions import my_bookings

PAGE_SIZE = 20


def my_bookings_page(start: int = 0, limit: int = PAGE_SIZE) -> MyBookingsPage:
	"""The session user's bookings, newest first."""
	rows = bookings_query(frappe.session.user).offset(start).limit(limit + 1).run(as_dict=True)
	return MyBookingsPage(
		bookings=[MyBooking(**row) for row in rows[:limit]], has_next_page=len(rows) > limit
	)


def bookings_query(user: str):
	booking = frappe.qb.DocType("Event Booking")
	event = frappe.qb.DocType("Buzz Event")
	return (
		frappe.qb.from_(booking)
		.join(event)
		.on(event.name == booking.event)
		.select(
			booking.name,
			booking.event,
			event.title.as_("event_title"),
			event.start_date.as_("event_start_date"),
			booking.status,
			booking.payment_status,
			booking.docstatus,
			booking.creation.as_("booked_at"),
		)
		.where(booking.name.isin(my_bookings(user)))
		.orderby(booking.creation, order=Order.desc)
	)
