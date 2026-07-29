import frappe
from frappe import _
from frappe.utils import format_date, format_time


@frappe.whitelist()
def validate_ticket_for_checkin(ticket_id: str) -> dict:
	frappe.only_for("Frontdesk Manager", True)
	if not frappe.db.exists("Event Ticket", ticket_id):
		frappe.throw(_("Ticket not found"))

	ticket_doc = frappe.get_cached_doc("Event Ticket", ticket_id)

	if ticket_doc.docstatus == 2:
		frappe.throw(_("This ticket has been cancelled and cannot be checked in"))

	event_doc = frappe.get_cached_doc("Buzz Event", ticket_doc.event)
	ticket_type_doc = (
		frappe.get_cached_doc("Event Ticket Type", ticket_doc.ticket_type) if ticket_doc.ticket_type else None
	)

	checkin_date = frappe.utils.today()
	existing_checkin = frappe.db.exists("Event Check In", {"ticket": ticket_id, "date": checkin_date})

	if existing_checkin:
		checkin_doc = frappe.get_doc("Event Check In", existing_checkin)
		formatted_checkin_time = (
			format_date(checkin_doc.creation) + " at " + format_time(checkin_doc.creation)
		)

		frappe.throw(_("This ticket was already checked in today ({0}).").format(formatted_checkin_time))

	add_ons = frappe.db.get_all(
		"Ticket Add-on Value",
		filters={"parent": ticket_id},
		fields=[
			"add_on",
			"add_on.title as add_on_title",
			"add_on.user_selects_option as add_on_selects_option",
			"value",
			"price",
			"currency",
		],
	)

	return {
		"message": _("Valid ticket ready for check-in"),
		"ticket": {
			"id": ticket_doc.name,
			"attendee_name": ticket_doc.attendee_name,
			"attendee_email": ticket_doc.attendee_email,
			"event_title": event_doc.title,
			"ticket_type": (ticket_type_doc.title if ticket_type_doc else ticket_doc.ticket_type),
			"venue": event_doc.venue,
			"start_date": event_doc.start_date,
			"start_time": event_doc.start_time,
			"end_date": event_doc.end_date,
			"end_time": event_doc.end_time,
			"is_checked_in": False,
			"check_in_time": None,
			"booking_id": ticket_doc.booking,
			"add_ons": add_ons,
		},
		"payment_details": get_payment_details_for_ticket(ticket_id),
	}


def get_payment_details_for_ticket(ticket_id: str) -> dict | None:
	booking_id = frappe.get_cached_value("Event Ticket", ticket_id, "booking")
	if not booking_id:
		return None

	payments = frappe.db.get_all(
		"Event Payment",
		filters={
			"reference_doctype": "Event Booking",
			"reference_docname": booking_id,
			"payment_received": 1,
		},
		fields=["name", "amount", "currency"],
		limit=1,
	)

	if payments:
		return payments[0]


@frappe.whitelist()
def checkin_ticket(ticket_id: str) -> dict:
	frappe.only_for("Frontdesk Manager", True)

	checkin_date = frappe.utils.today()
	validation_result = validate_ticket_for_checkin(ticket_id)

	checkin_doc = frappe.new_doc("Event Check In")
	checkin_doc.ticket = ticket_id
	checkin_doc.date = checkin_date
	checkin_doc.insert(ignore_permissions=True)
	checkin_doc.submit()

	return {
		"message": _("Successfully checked in {attendee_name} for {checkin_date}").format(
			attendee_name=validation_result["ticket"]["attendee_name"],
			checkin_date=frappe.format(checkin_date, {"fieldtype": "Date"}),
		),
		"ticket": {
			**validation_result["ticket"],
			"is_checked_in": True,
			"check_in_time": checkin_doc.creation,
			"check_in_date": checkin_date,
		},
	}
