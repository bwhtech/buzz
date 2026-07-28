import frappe
from frappe import _
from frappe.utils import days_diff, format_date, format_time, today


def is_ticket_transfer_allowed(event_id: str | int) -> bool:
	try:
		event = frappe.get_cached_doc("Buzz Event", event_id)
		settings = frappe.get_single("Buzz Settings")
		transfer_cutoff_days = settings.get("allow_transfer_ticket_before_event_start_days", 7)

		if not event.start_date:
			return False

		return days_diff(event.start_date, today()) >= transfer_cutoff_days
	except Exception as e:
		frappe.log_error(f"Error checking ticket transfer eligibility: {e!s}")
		return False


def is_add_on_change_allowed(event_id: str | int) -> bool:
	try:
		event = frappe.get_cached_doc("Buzz Event", event_id)
		settings = frappe.get_cached_doc("Buzz Settings")
		add_on_change_cutoff_days = settings.get("allow_add_ons_change_before_event_start_days", 7)

		if not event.start_date:
			return False

		return days_diff(event.start_date, today()) >= add_on_change_cutoff_days
	except Exception as e:
		frappe.log_error(f"Error checking add-on change eligibility: {e!s}")
		return False


def is_cancellation_request_allowed(event_id: str | int) -> bool:
	try:
		event = frappe.get_cached_doc("Buzz Event", event_id)
		settings = frappe.get_cached_doc("Buzz Settings")
		cancellation_cutoff_days = settings.get(
			"allow_ticket_cancellation_request_before_event_start_days", 7
		)

		if not event.start_date:
			return False

		return days_diff(event.start_date, today()) >= cancellation_cutoff_days
	except Exception as e:
		frappe.log_error(f"Error checking cancellation request eligibility: {e!s}")
		return False


@frappe.whitelist()
def can_transfer_ticket(event_id: str | int) -> dict:
	return {"can_transfer": is_ticket_transfer_allowed(event_id), "event_id": event_id}


@frappe.whitelist()
def can_change_add_ons(event_id: str | int) -> dict:
	return {"can_change_add_ons": is_add_on_change_allowed(event_id), "event_id": event_id}


@frappe.whitelist()
def can_request_cancellation(event_id: str | int) -> dict:
	return {"can_request_cancellation": is_cancellation_request_allowed(event_id), "event_id": event_id}


def create_add_on_doc(attendee_name: str, add_ons: list[dict]):
	for add_on in add_ons:
		add_on["currency"] = frappe.db.get_value("Ticket Add-on", add_on["add_on"], "currency")

	return frappe.get_doc(
		{"doctype": "Attendee Ticket Add-on", "add_ons": add_ons, "attendee_name": attendee_name}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def transfer_ticket(ticket_id: str, new_first_name: str, new_last_name: str, new_email: str):
	if not frappe.db.exists("Event Ticket", ticket_id):
		frappe.throw(frappe._("Ticket not found."))

	ticket = frappe.get_doc("Event Ticket", ticket_id)
	booking_user = frappe.db.get_value("Event Booking", ticket.booking, "user")

	if (
		ticket.attendee_email != frappe.session.user
		and booking_user != frappe.session.user
		and not frappe.has_permission("Event Ticket", "write", ticket)
	):
		frappe.throw(frappe._("Not permitted to transfer this ticket."))

	if not is_ticket_transfer_allowed(ticket.event):
		frappe.throw(frappe._("Ticket transfer is not allowed at this time. The transfer window has closed."))

	old_name = ticket.attendee_name
	old_email = ticket.attendee_email
	new_name = f"{new_first_name} {new_last_name}".strip()

	ticket.first_name = new_first_name
	ticket.last_name = new_last_name
	ticket.attendee_email = new_email
	ticket.save(ignore_permissions=True)

	send_ticket_transfer_emails(ticket.name, old_name, old_email, new_name, new_email)


def send_ticket_transfer_emails(ticket_id: str, old_name: str, old_email: str, new_name: str, new_email: str):
	try:
		ticket = frappe.get_doc("Event Ticket", ticket_id)
		event = frappe.get_doc("Buzz Event", ticket.event)
		booking = frappe.get_doc("Event Booking", ticket.booking)

		old_attendee_subject = f"Your ticket for {event.title} has been transferred"
		old_attendee_message = f"""
		<p>Dear {old_name},</p>

		<p>This is to inform you that your ticket for <strong>{event.title}</strong> has been transferred to {new_name} ({new_email}).</p>

		<p><strong>Event Details:</strong></p>
		<ul>
			<li><strong>Event:</strong> {event.title}</li>
			<li><strong>Date:</strong> {format_date(event.start_date)}</li>
			<li><strong>Ticket Type:</strong> {ticket.ticket_type}</li>
			<li><strong>Booking ID:</strong> {booking.name}</li>
		</ul>

		<p>If you have any questions about this transfer, please contact us.</p>

		<p>Best regards,<br>
		{event.title} Team</p>
		"""

		frappe.sendmail(
			recipients=[old_email], subject=old_attendee_subject, message=old_attendee_message, delayed=False
		)

		new_attendee_subject = f"Welcome! Your ticket for {event.title}"
		new_attendee_message = f"""
		<p>Dear {new_name},</p>

		<p>Great news! A ticket for <strong>{event.title}</strong> has been transferred to you.</p>

		<p><strong>Event Details:</strong></p>
		<ul>
			<li><strong>Event:</strong> {event.title}</li>
			<li><strong>Date:</strong> {format_date(event.start_date)}</li>
			<li><strong>Time:</strong> {format_time(event.start_time) if event.start_time else "TBA"}</li>
			<li><strong>Venue:</strong> {event.venue or "TBA"}</li>
			<li><strong>Ticket Type:</strong> {ticket.ticket_type}</li>
			<li><strong>Booking ID:</strong> {booking.name}</li>
		</ul>

		<p><strong>Your Ticket Details:</strong></p>
		<ul>
			<li><strong>Ticket ID:</strong> {ticket.name}</li>
			<li><strong>Attendee Name:</strong> {new_name}</li>
			<li><strong>Email:</strong> {new_email}</li>
		</ul>

		<p>Please save this email for your records. You may need to present this ticket information at the event entrance.</p>

		<p>We look forward to seeing you at the event!</p>

		<p>Best regards,<br>
		{event.title} Team</p>
		"""

		frappe.sendmail(
			recipients=[new_email], subject=new_attendee_subject, message=new_attendee_message, delayed=False
		)

	except Exception as e:
		frappe.log_error(f"Failed to send ticket transfer emails for ticket {ticket_id}: {e!s}")


@frappe.whitelist()
def change_add_on_preference(add_on_id: str, new_value: str):
	if not frappe.db.exists("Ticket Add-on Value", add_on_id):
		frappe.throw(frappe._("Add-on value not found."))

	add_on_value = frappe.get_cached_doc("Ticket Add-on Value", add_on_id)
	ticket = frappe.get_cached_doc("Event Ticket", add_on_value.parent)

	if not is_add_on_change_allowed(ticket.event):
		frappe.throw(
			frappe._(
				"Add-on changes are not allowed at this time. The change window has closed as the event is approaching."
			)
		)

	frappe.db.set_value(
		"Ticket Add-on Value",
		add_on_id,
		"value",
		new_value,
	)


@frappe.whitelist()
def get_ticket_details(ticket_id: str) -> dict:
	details = frappe._dict()
	ticket_doc = frappe.get_cached_doc("Event Ticket", ticket_id)

	if frappe.session.user != "Administrator":
		if ticket_doc.attendee_email != frappe.session.user:
			frappe.throw(frappe._("Not permitted to view this ticket"))

	details.doc = ticket_doc

	add_ons = frappe.db.get_all(
		"Ticket Add-on Value",
		filters={"parent": ticket_id},
		fields=[
			"name",
			"add_on",
			"add_on.title as add_on_title",
			"value",
			"price",
			"currency",
			"add_on.user_selects_option as user_selects_option",
		],
	)

	event_add_ons = frappe.db.get_all(
		"Ticket Add-on",
		filters={"event": ticket_doc.event, "user_selects_option": True},
		fields=["name", "title", "user_selects_option", "options"],
	)

	add_on_options_map = {}
	for event_add_on in event_add_ons:
		if event_add_on.user_selects_option:
			add_on_options_map[event_add_on.name] = (
				event_add_on.options.split("\n") if event_add_on.options else []
			)

	enhanced_add_ons = []
	for add_on in add_ons:
		add_on_data = {
			"id": add_on.name,
			"name": add_on.add_on,
			"title": add_on.add_on_title,
			"value": add_on.value,
			"price": add_on.price,
			"currency": add_on.currency,
			"user_selects_option": add_on.user_selects_option,
			"options": add_on_options_map.get(add_on.add_on, []),
		}
		enhanced_add_ons.append(add_on_data)

	details.add_ons = enhanced_add_ons
	details.event = frappe.get_cached_doc("Buzz Event", ticket_doc.event)

	booking_doc = None
	if ticket_doc.booking:
		booking_doc = frappe.get_cached_doc("Event Booking", ticket_doc.booking)
		if booking_doc.owner == frappe.session.user:
			details.booking = booking_doc
		else:
			details.booking = None
	else:
		details.booking = None

	details.ticket_type = frappe.get_cached_doc("Event Ticket Type", ticket_doc.ticket_type)
	details.can_transfer_ticket = (
		can_transfer_ticket(details.event.name) if details.event else {"can_transfer": False}
	)
	details.can_change_add_ons = (
		can_change_add_ons(details.event.name) if details.event else {"can_change_add_ons": False}
	)
	details.can_request_cancellation = (
		can_request_cancellation(details.event.name) if details.event else {"can_request_cancellation": False}
	)

	details.zoom_join_url = None
	if hasattr(ticket_doc, "zoom_session_registration") and ticket_doc.zoom_session_registration:
		zoom_registration = frappe.db.get_value(
			"Zoom Session Registration",
			ticket_doc.zoom_session_registration,
			["join_url", "reference_doctype", "reference_name"],
			as_dict=True,
		)
		if zoom_registration:
			details.zoom_join_url = zoom_registration.join_url
			details.zoom_reference_doctype = zoom_registration.reference_doctype
			details.zoom_reference_name = zoom_registration.reference_name

	return details


@frappe.whitelist()
def create_cancellation_request(booking_id: str, ticket_ids: list | None = None) -> dict:
	booking_doc = frappe.get_cached_doc("Event Booking", booking_id)

	if booking_doc.user != frappe.session.user and not frappe.has_permission(
		"Event Booking", "write", booking_doc
	):
		frappe.throw(frappe._("Not permitted to request cancellation for this booking."))

	if not is_cancellation_request_allowed(booking_doc.event):
		frappe.throw(_("Cancellation requests are no longer allowed for this event."))

	existing_request = frappe.db.exists(
		"Ticket Cancellation Request", {"booking": booking_id, "docstatus": 0}
	)
	if existing_request:
		frappe.throw(_("A cancellation request already exists for this booking."))

	all_tickets = frappe.db.get_all("Event Ticket", filters={"booking": booking_id}, fields=["name"])
	cancel_full_booking = not ticket_ids or len(ticket_ids) == len(all_tickets)

	cancellation_request = frappe.new_doc("Ticket Cancellation Request")
	cancellation_request.booking = booking_id
	cancellation_request.cancel_full_booking = cancel_full_booking

	if not cancel_full_booking and ticket_ids:
		for ticket_id in ticket_ids:
			ticket_booking = frappe.db.get_value("Event Ticket", ticket_id, "booking")
			if ticket_booking != booking_id:
				frappe.throw(f"Ticket {ticket_id} does not belong to booking {booking_id}")

			cancellation_request.append("tickets", {"ticket": ticket_id})

	cancellation_request.insert(ignore_permissions=True)
