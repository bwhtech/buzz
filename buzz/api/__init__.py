import hashlib
import hmac
import os
from base64 import b32encode

import frappe
import pyotp
from frappe import _
from frappe.auth import LoginAttemptTracker
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.rate_limiter import rate_limit
from frappe.translate import get_all_translations
from frappe.utils import (
	days_diff,
	format_date,
	format_time,
	get_datetime,
	get_datetime_in_timezone,
	get_system_timezone,
	now_datetime,
	today,
	validate_email_address,
)
from frappe.utils.password import get_encryption_key

from buzz.payments import (
	get_payment_gateways_for_event,
	get_payment_link_for_booking,
	get_payment_link_for_sponsorship,
)
from buzz.utils import build_event_datetimes, is_app_installed

OFFLINE_PAYMENT_METHOD = "Offline"


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@rate_limit(key="identifier", limit=5, seconds=3600)
def send_guest_booking_otp(event: int, identifier: str) -> dict:
	event_doc = frappe.get_cached_doc("Buzz Event", event)

	if not event_doc.allow_guest_booking:
		frappe.throw(_("Guest booking is not enabled for this event"))

	if event_doc.guest_verification_method == "None":
		frappe.throw(_("OTP verification is not enabled for this event"))

	channel = "phone" if event_doc.guest_verification_method == "Phone OTP" else "email"

	identifier = identifier.strip()
	if not identifier:
		frappe.throw(_("Email or phone is required"))

	if channel == "email":
		identifier = identifier.lower()
		validate_email_address(identifier, throw=True)

	otp_secret = b32encode(os.urandom(10)).decode("utf-8")
	otp_code = pyotp.HOTP(otp_secret).at(0)
	cache_key = f"guest_booking_otp:{channel}:{identifier}"

	if frappe.in_test:
		frappe.cache.set_value(cache_key, otp_secret, expires_in_sec=600)
		return {"otp": otp_code}

	try:
		if channel == "email":
			frappe.sendmail(
				recipients=[identifier],
				subject=_("Your Booking Verification Code"),
				message=_(
					"Your verification code is: <b>{0}</b><br><br>This code expires in 10 minutes."
				).format(otp_code),
				now=True,
			)
		else:
			send_sms(
				receiver_list=[identifier],
				msg=_("Your booking verification code is: {0}. It expires in 10 minutes.").format(otp_code),
			)
	except Exception:
		frappe.throw(_("Failed to send verification code. Please try again."))

	frappe.cache.set_value(cache_key, otp_secret, expires_in_sec=600)


def verify_guest_otp(channel: str, identifier: str, otp: str):
	cache_key = f"guest_booking_otp:{channel}:{identifier}"
	tracker = LoginAttemptTracker(
		key=f"guest_otp:{channel}:{identifier}",
		max_consecutive_login_attempts=5,
		lock_interval=600,
	)

	if not tracker.is_user_allowed():
		frappe.throw(_("Too many failed attempts. Please try again later."))

	otp_secret = frappe.cache.get_value(cache_key)
	if not otp_secret:
		frappe.throw(_("Verification code expired. Please request a new one."))

	if not pyotp.HOTP(otp_secret).verify(otp.strip(), 0):
		tracker.add_failure_attempt()
		frappe.throw(_("Invalid verification code"))

	frappe.cache.delete_value(cache_key)
	tracker.add_success_attempt()


def get_or_create_guest_user(email: str, full_name: str) -> str:
	email = email.lower().strip()

	validate_email_address(email, throw=True)
	if frappe.db.exists("User", email):
		return email

	name_parts = full_name.strip().split(" ", 1)
	first_name = name_parts[0] if name_parts else "Guest"
	last_name = name_parts[1] if len(name_parts) > 1 else ""

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"enabled": 1,
			"user_type": "Website User",
			"send_welcome_email": 0,
		}
	)
	user.insert(ignore_permissions=True)

	return email


@frappe.whitelist()
def get_event_payment_gateways(event: str) -> list[str]:
	return get_payment_gateways_for_event(event)


def are_registrations_closed(event_doc) -> bool:
	event_timezone = event_doc.time_zone or get_system_timezone()
	current_datetime_in_event_timezone = get_datetime_in_timezone(event_timezone).replace(tzinfo=None)

	if event_doc.registrations_close_at:
		return current_datetime_in_event_timezone > get_datetime(event_doc.registrations_close_at)

	# No explicit cutoff set - registrations close once the event itself has ended.
	_, event_end_datetime = build_event_datetimes(event_doc)
	return current_datetime_in_event_timezone > event_end_datetime


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


@frappe.whitelist()
def can_transfer_ticket(event_id: str | int) -> dict:
	return {"can_transfer": is_ticket_transfer_allowed(event_id), "event_id": event_id}


@frappe.whitelist()
def can_change_add_ons(event_id: str | int) -> dict:
	return {"can_change_add_ons": is_add_on_change_allowed(event_id), "event_id": event_id}


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
def can_request_cancellation(event_id: str | int) -> dict:
	return {"can_request_cancellation": is_cancellation_request_allowed(event_id), "event_id": event_id}


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_event_booking_data(event_route: str) -> dict:
	data = frappe._dict()
	event_doc = frappe.get_cached_doc("Buzz Event", {"route": event_route})

	if not event_doc.is_published:
		frappe.throw(_("Event not found"), frappe.DoesNotExistError)

	data.registrations_closed = are_registrations_closed(event_doc)

	is_guest = frappe.session.user == "Guest"
	if is_guest:
		data.event_details = {
			"name": event_doc.name,
			"title": event_doc.title,
			"route": event_doc.route,
			"start_date": event_doc.start_date,
			"end_date": event_doc.end_date,
			"start_time": event_doc.start_time,
			"end_time": event_doc.end_time,
			"time_zone": event_doc.time_zone,
			"venue": event_doc.venue,
			"medium": event_doc.medium,
			"category": event_doc.category,
			"banner_image": event_doc.banner_image,
			"short_description": event_doc.short_description,
			"free_webinar": event_doc.free_webinar,
			"send_ticket_email": event_doc.send_ticket_email,
			"allow_guest_booking": event_doc.allow_guest_booking,
			"guest_verification_method": event_doc.guest_verification_method,
			"default_ticket_type": event_doc.default_ticket_type,
		}
	else:
		data.event_details = event_doc

	available_ticket_types = []
	published_ticket_types = frappe.db.get_all(
		"Event Ticket Type", filters={"is_published": True, "event": event_doc.name}, pluck="name"
	)
	for ticket_type in published_ticket_types:
		tt = frappe.get_cached_doc("Event Ticket Type", ticket_type)
		if tt.are_tickets_available(1):
			available_ticket_types.append(tt)
	data.available_ticket_types = available_ticket_types

	add_ons = frappe.db.get_all(
		"Ticket Add-on", filters={"event": event_doc.name, "enabled": 1}, fields=["*"], order_by="title"
	)

	for add_on in add_ons:
		if add_on.user_selects_option:
			add_on.options = add_on.options.split("\n")

	data.available_add_ons = add_ons

	data.tax_settings = {
		"apply_tax": event_doc.apply_tax,
		"tax_inclusive": event_doc.tax_inclusive,
		"tax_label": event_doc.tax_label or "Tax",
		"tax_percentage": event_doc.tax_percentage or 0,
	}

	custom_fields = frappe.db.get_all(
		"Buzz Custom Field",
		filters={"event": event_doc.name, "enabled": 1},
		fields=["*"],
		order_by="order",
	)
	data.custom_fields = custom_fields

	payment_gateways = get_payment_gateways_for_event(event_doc.name)

	offline_methods_raw = frappe.get_all(
		"Offline Payment Method",
		filters={"event": event_doc.name, "enabled": 1},
		fields=["name", "title", "description", "collect_payment_proof"],
		order_by="creation",
	)

	offline_methods = []
	for method in offline_methods_raw:
		method_custom_fields = frappe.get_all(
			"Buzz Custom Field",
			filters={
				"event": event_doc.name,
				"enabled": 1,
				"applied_to": "Offline Payment Form",
				"offline_payment_method": method.name,
			},
			fields=["*"],
			order_by="order",
		)
		offline_methods.append(
			{
				"name": method.name,
				"title": method.title,
				"description": method.description,
				"collect_payment_proof": method.collect_payment_proof,
				"custom_fields": method_custom_fields,
			}
		)
		payment_gateways.append(method.title)

	data.payment_gateways = payment_gateways
	data.offline_payment_enabled = len(offline_methods) > 0
	data.offline_methods = offline_methods

	return data


def validate_custom_fields(custom_fields_data: dict, phone_field_map: dict) -> None:
	for field_name, field_value in custom_fields_data.items():
		if field_value and field_name in phone_field_map:
			frappe.utils.validate_phone_number_with_country_code(
				str(field_value), phone_field_map[field_name]
			)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def process_booking(
	attendees: list[dict],
	event: str,
	coupon_code: str | None = None,
	booking_custom_fields: dict | None = None,
	payment_gateway: str | None = None,
	utm_parameters: list[dict] | None = None,
	guest_email: str | None = None,
	guest_full_name: str | None = None,
	otp: str | None = None,
	guest_phone: str | None = None,
	payment_proof: str | None = None,
	is_offline: bool = False,
	offline_payment_method: str | None = None,
	invoice_requested: bool = False,
	tax_id: str | None = None,
	billing_address: str | None = None,
) -> dict:
	event_doc = frappe.get_cached_doc("Buzz Event", event)
	if not event_doc.is_published:
		frappe.throw(_("Event is not live"))

	if are_registrations_closed(event_doc):
		frappe.throw(_("Registrations for this event are closed"))

	is_guest = frappe.session.user == "Guest"

	if is_guest:
		if not event_doc.allow_guest_booking:
			frappe.throw(_("Please log in to access this feature"), frappe.AuthenticationError)

		if not guest_email:
			frappe.throw(_("Email is required for guest booking"))

		validate_email_address(guest_email, throw=True)
		email = guest_email.lower().strip()

		if event_doc.guest_verification_method == "Email OTP":
			if not otp:
				frappe.throw(_("Verification code is required"))
			verify_guest_otp("email", email, otp)

		elif event_doc.guest_verification_method == "Phone OTP":
			if not otp:
				frappe.throw(_("Verification code is required"))
			if not guest_phone:
				frappe.throw(_("Phone number is required"))
			verify_guest_otp("phone", guest_phone.strip(), otp)

		first_name = (attendees[0].get("first_name") or "").strip()
		last_name = (attendees[0].get("last_name") or "").strip()
		full_name = (guest_full_name or "").strip() or f"{first_name} {last_name}".strip()
		if not full_name:
			frappe.throw(_("Full name is required for guest booking"))
		booking_user = get_or_create_guest_user(guest_email, full_name)
	else:
		booking_user = frappe.session.user

	booking = frappe.new_doc("Event Booking")
	booking.event = event
	booking.coupon_code = coupon_code
	booking.user = booking_user

	if event_doc.apply_tax and invoice_requested:
		booking.invoice_requested = 1
		booking.tax_id = tax_id
		booking.billing_address = billing_address

	if utm_parameters:
		for utm_param in utm_parameters:
			booking.append(
				"utm_parameters",
				{
					"utm_name": utm_param.get("utm_name"),
					"value": utm_param.get("value"),
				},
			)

	if booking_custom_fields:
		booking_custom_field_defs = frappe.db.get_all(
			"Buzz Custom Field",
			filters={"event": event, "enabled": 1, "applied_to": "Booking"},
			fields=["fieldname", "label", "fieldtype"],
		)
		custom_field_map = {cf["fieldname"]: cf for cf in booking_custom_field_defs}

		for field_name, field_value in booking_custom_fields.items():
			if field_value and field_name in custom_field_map:
				field_def = custom_field_map[field_name]
				booking.append(
					"additional_fields",
					{
						"fieldname": field_name,
						"value": str(field_value),
						"label": field_def["label"],
						"fieldtype": field_def["fieldtype"],
					},
				)

	phone_fields = frappe.db.get_all(
		"Buzz Custom Field",
		filters={"event": event, "enabled": 1, "fieldtype": "Phone"},
		fields=["fieldname", "label"],
	)
	phone_map = {cf["fieldname"]: cf["label"] for cf in phone_fields}

	if event_doc.category == "Webinars":
		for attendee in attendees:
			if not (attendee.get("last_name") or "").strip():
				frappe.throw(_("Last name is required for all attendees in webinar events"))

	for attendee in attendees:
		first_name = (attendee.get("first_name") or "").strip()
		last_name = (attendee.get("last_name") or "").strip()

		if not first_name and attendee.get("full_name"):
			name_parts = attendee["full_name"].strip().split(" ", 1)
			first_name = name_parts[0]
			last_name = last_name or (name_parts[1] if len(name_parts) > 1 else "")

		attendee_full_name = f"{first_name} {last_name}".strip()

		add_ons = attendee.get("add_ons", None)
		if add_ons:
			add_ons = create_add_on_doc(
				attendee_name=attendee_full_name,
				add_ons=add_ons,
			)

		custom_fields = attendee.get("custom_fields", {})
		if custom_fields:
			validate_custom_fields(custom_fields, phone_map)
		attendee_row = {
			"first_name": first_name,
			"last_name": last_name,
			"email": attendee.get("email"),
			"ticket_type": attendee.get("ticket_type"),
			"add_ons": add_ons.name if add_ons else None,
			"custom_fields": custom_fields if custom_fields else None,
		}

		booking.append("attendees", attendee_row)

	booking.insert(ignore_permissions=True)
	frappe.db.commit()

	if booking.total_amount == 0:
		booking.flags.ignore_permissions = True
		booking.submit()
		return {
			"booking_name": booking.name,
			"redirect_to": f"/booking-success/{booking.name}?token={get_booking_access_token(booking.name)}",
		}

	if is_offline:
		method_filters = {"event": event, "enabled": 1}
		if offline_payment_method:
			method_filters["name"] = offline_payment_method
		method_doc = frappe.db.get_value(
			"Offline Payment Method", method_filters, ["name", "title"], as_dict=True
		)
		if not method_doc:
			frappe.throw(_("Offline payment is not enabled for this event"))

		booking.payment_method = OFFLINE_PAYMENT_METHOD
		booking.offline_payment_method = method_doc.title

		booking.status = "Approval Pending"
		booking.payment_status = "Verification Pending"
		booking.flags.ignore_permissions = True
		booking.save()

		if payment_proof:
			try:
				file_doc = frappe.get_doc(
					{
						"doctype": "File",
						"file_url": payment_proof,
						"attached_to_doctype": "Event Booking",
						"attached_to_name": booking.name,
						"is_private": 1,
					}
				)
				file_doc.insert(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(f"Failed to attach payment proof: {e}")

		return {"booking_name": booking.name, "offline_payment": True}

	return {
		"payment_link": get_payment_link_for_booking(
			booking.name,
			redirect_to=f"/dashboard/booking-success/{booking.name}?token={get_booking_access_token(booking.name)}",
			payment_gateway=payment_gateway,
		)
	}


def get_booking_access_token(booking_name: str) -> str:
	"""HMAC of the booking name signed with the site encryption_key.

	Lets a guest (whose browser session stays "Guest") open their own booking
	confirmation without logging in, while keeping sequential booking names
	unguessable (no IDOR)."""
	key = get_encryption_key().encode()
	return hmac.new(key, booking_name.encode(), hashlib.sha256).hexdigest()


def verify_booking_access_token(booking_name: str, token: str | None) -> bool:
	return bool(token) and hmac.compare_digest(get_booking_access_token(booking_name), token)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_booking_confirmation(booking_id: str, token: str | None = None) -> dict:
	"""Read-only booking confirmation for the post-payment success page.

	Authorized by a valid access token (guest flow) OR read permission on the
	booking (logged-in owner). Returns a minimal payload — no transfer/cancel data.
	"""
	# nosemgrep: frappe-semgrep-rules.rules.unchecked-frappe-permission-call -- return value checked below
	authorized = verify_booking_access_token(booking_id, token) or frappe.has_permission(
		"Event Booking", "read", doc=booking_id
	)
	if not authorized:
		frappe.throw(_("You are not allowed to view this booking."), frappe.PermissionError)

	booking_doc = frappe.get_cached_doc("Event Booking", booking_id)
	event_doc = frappe.get_cached_doc("Buzz Event", booking_doc.event)

	tickets = frappe.db.get_all(
		"Event Ticket",
		filters={"booking": booking_id},
		fields=[
			"name",
			"attendee_name",
			"attendee_email",
			"ticket_type.title as ticket_type",
			"qr_code",
		],
	)

	venue = None
	if event_doc.venue:
		venue_doc = frappe.get_cached_doc("Event Venue", event_doc.venue)
		venue = {"name": venue_doc.name, "address": venue_doc.get("address")}

	return frappe._dict(
		{
			"event": {
				"title": event_doc.title,
				"route": event_doc.route,
				"start_date": event_doc.start_date,
				"end_date": event_doc.end_date,
				"start_time": event_doc.start_time,
				"end_time": event_doc.end_time,
				"short_description": event_doc.get("short_description"),
				"free_webinar": event_doc.get("free_webinar"),
			},
			"venue": venue,
			"booking": {
				"name": booking_doc.name,
				"total_amount": booking_doc.total_amount,
				"net_amount": booking_doc.net_amount,
				"currency": booking_doc.currency,
				"payment_status": booking_doc.payment_status,
				"status": booking_doc.status,
				"tax_amount": booking_doc.tax_amount,
				"tax_label": booking_doc.tax_label,
				"tax_percentage": booking_doc.tax_percentage,
				"discount_amount": booking_doc.discount_amount,
				"coupon_code": booking_doc.coupon_code,
			},
			"tickets": tickets,
		}
	)


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
def get_booking_details(booking_id: str) -> dict:
	details = frappe._dict()
	booking_doc = frappe.get_cached_doc("Event Booking", booking_id)
	details.doc = booking_doc

	tickets = frappe.db.get_all(
		"Event Ticket",
		filters={"booking": booking_id},
		fields=[
			"name",
			"attendee_name",
			"attendee_email",
			"ticket_type.title as ticket_type",
			"qr_code",
			"event",
			"docstatus",
		],
	)

	add_ons = frappe.db.get_all(
		"Ticket Add-on Value",
		filters={"parent": ("in", [ticket.name for ticket in tickets])},
		fields=[
			"parent",
			"name",
			"add_on",
			"value",
			"add_on.title as add_on_title",
			"add_on.user_selects_option as user_selects_option",
		],
	)

	event_add_ons = frappe.db.get_all(
		"Ticket Add-on",
		filters={"event": booking_doc.event, "user_selects_option": True},
		fields=["name", "title", "user_selects_option", "options"],
	)

	add_on_options_map = {}
	for event_add_on in event_add_ons:
		if event_add_on.user_selects_option:
			add_on_options_map[event_add_on.name] = (
				event_add_on.options.split("\n") if event_add_on.options else []
			)

	for ticket in tickets:
		ticket.add_ons = []
		for add_on in add_ons:
			if add_on.parent == ticket.name:
				add_on_data = {
					"id": add_on.name,
					"name": add_on.add_on,
					"title": add_on.add_on_title,
					"value": add_on.value,
					"user_selects_option": add_on.user_selects_option,
					"options": add_on_options_map.get(add_on.add_on, []),
				}
				ticket.add_ons.append(add_on_data)
		ticket.add_ons = sorted(ticket.add_ons, key=lambda x: x["title"])

	details.tickets = tickets
	details.event = frappe.get_cached_doc("Buzz Event", booking_doc.event)

	if details.event.venue:
		details.venue = frappe.get_cached_doc("Event Venue", details.event.venue)

	details.can_transfer_ticket = can_transfer_ticket(details.event.name)
	details.can_change_add_ons = can_change_add_ons(details.event.name)
	details.can_request_cancellation = can_request_cancellation(details.event.name)

	existing_cancellation = frappe.db.get_value(
		"Ticket Cancellation Request",
		{"booking": booking_id},
		["name", "cancel_full_booking", "creation", "status", "docstatus"],
		as_dict=True,
	)
	details.cancellation_request = existing_cancellation

	details.cancellation_requested_tickets = []

	if existing_cancellation and existing_cancellation.docstatus == 0:
		if existing_cancellation.cancel_full_booking:
			details.cancellation_requested_tickets = [ticket.name for ticket in tickets]
		else:
			requested_tickets = frappe.db.get_all(
				"Ticket Cancellation Item", filters={"parent": existing_cancellation.name}, fields=["ticket"]
			)
			details.cancellation_requested_tickets = [item.ticket for item in requested_tickets]

	details.cancelled_tickets = [ticket.name for ticket in tickets if ticket.docstatus == 2]

	return details


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
def get_sponsorship_details(enquiry_id: str) -> dict:
	enquiry = frappe.get_doc("Sponsorship Enquiry", enquiry_id)

	if enquiry.owner != frappe.session.user and not frappe.has_permission(
		"Sponsorship Enquiry", "read", enquiry
	):
		frappe.throw(frappe._("Not permitted to view this sponsorship enquiry"))

	tier_title = ""
	if enquiry.tier:
		tier_title = frappe.db.get_value("Sponsorship Tier", enquiry.tier, "title") or enquiry.tier

	event_details = {}
	if enquiry.event:
		event = frappe.get_cached_doc("Buzz Event", enquiry.event)
		event_details = {
			"title": event.title,
			"short_description": getattr(event, "short_description", ""),
			"about": getattr(event, "about", ""),
			"start_date": event.start_date,
			"end_date": getattr(event, "end_date", ""),
			"venue": getattr(event, "venue", ""),
			"route": getattr(event, "route", ""),
		}

	sponsor_details = None
	sponsors = frappe.db.get_all(
		"Event Sponsor",
		filters={"enquiry": enquiry_id},
		fields=["name", "company_name", "company_logo", "creation", "event", "tier"],
		limit=1,
	)

	if sponsors:
		sponsor_details = sponsors[0]
		if sponsor_details.get("tier"):
			sponsor_tier_title = frappe.db.get_value("Sponsorship Tier", sponsor_details["tier"], "title")
			sponsor_details["tier_title"] = sponsor_tier_title or sponsor_details["tier"]

	return {
		"enquiry": {
			"name": enquiry.name,
			"company_name": enquiry.company_name,
			"company_logo": enquiry.company_logo,
			"event": enquiry.event,
			"tier": enquiry.tier,
			"tier_title": tier_title,
			"status": enquiry.status,
			"creation": enquiry.creation,
			"owner": enquiry.owner,
		},
		"event_details": event_details,
		"sponsor_details": sponsor_details,
		"has_sponsor": bool(sponsor_details),
	}


@frappe.whitelist()
def get_user_sponsorship_inquiries() -> list:
	inquiries = frappe.db.get_all(
		"Sponsorship Enquiry",
		filters={"owner": frappe.session.user},
		fields=["name", "company_name", "event", "tier", "status", "creation"],
		order_by="creation desc",
	)

	for inquiry in inquiries:
		if inquiry.event:
			event_title = frappe.db.get_value("Buzz Event", inquiry.event, "title")
			inquiry["event_title"] = event_title

		if inquiry.tier:
			tier_title = frappe.db.get_value("Sponsorship Tier", inquiry.tier, "title")
			inquiry["tier_title"] = tier_title or inquiry.tier
		else:
			inquiry["tier_title"] = ""

	inquiry_names = [inquiry.name for inquiry in inquiries]
	if inquiry_names:
		sponsors = frappe.db.get_all(
			"Event Sponsor",
			filters={"enquiry": ["in", inquiry_names]},
			fields=["enquiry"],
		)
		sponsored_inquiries = {sponsor.enquiry for sponsor in sponsors}

		for inquiry in inquiries:
			inquiry["has_sponsor"] = inquiry.name in sponsored_inquiries
	else:
		for inquiry in inquiries:
			inquiry["has_sponsor"] = False

	return inquiries


@frappe.whitelist()
def create_sponsorship_payment_link(enquiry_id: str, tier_id: str, payment_gateway: str | None = None) -> str:
	enquiry = frappe.get_doc("Sponsorship Enquiry", enquiry_id)
	if enquiry.owner != frappe.session.user:
		frappe.throw(frappe._("Not permitted to create payment for this enquiry"))

	redirect_url = f"/dashboard/account/sponsorships/{enquiry_id}?success=true"
	return get_payment_link_for_sponsorship(
		enquiry_id, tier_id, redirect_url, payment_gateway=payment_gateway
	)


@frappe.whitelist()
def withdraw_sponsorship_enquiry(enquiry_id: str):
	enquiry = frappe.get_cached_doc("Sponsorship Enquiry", enquiry_id)
	if enquiry.owner != frappe.session.user:
		frappe.throw(frappe._("Not permitted to withdraw this enquiry"))

	if enquiry.status == "Paid":
		frappe.throw(frappe._("Cannot withdraw a paid sponsorship enquiry"))

	if enquiry.status == "Withdrawn":
		frappe.throw(frappe._("This sponsorship enquiry has already been withdrawn"))

	enquiry.status = "Withdrawn"
	enquiry.save(ignore_permissions=True)


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
	if hasattr(ticket_doc, "zoom_webinar_registration") and ticket_doc.zoom_webinar_registration:
		zoom_registration = frappe.db.get_value(
			"Zoom Webinar Registration",
			ticket_doc.zoom_webinar_registration,
			["join_url", "webinar"],
			as_dict=True,
		)
		if zoom_registration:
			details.zoom_join_url = zoom_registration.join_url
			details.zoom_webinar = zoom_registration.webinar

	return details


@frappe.whitelist()
def create_cancellation_request(booking_id: str, ticket_ids: list | None = None) -> dict:
	booking_doc = frappe.get_cached_doc("Event Booking", booking_id)

	if booking_doc.user != frappe.session.user and not frappe.has_permission(
		"Event Booking", "write", booking_doc
	):
		frappe.throw(frappe._("Not permitted to request cancellation for this booking."))

	if not is_cancellation_request_allowed(booking_doc.event):
		frappe.throw("Cancellation requests are no longer allowed for this event.")

	existing_request = frappe.db.exists(
		"Ticket Cancellation Request", {"booking": booking_id, "docstatus": 0}
	)
	if existing_request:
		frappe.throw("A cancellation request already exists for this booking.")

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


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_user_info() -> dict:
	if frappe.session.user == "Guest":
		return {
			"is_logged_in": False,
			"brand_image": frappe.get_cached_value("Website Settings", "Website Settings", "banner_image"),
		}

	user = frappe.get_cached_doc("User", frappe.session.user)

	return {
		"name": user.name,
		"is_logged_in": True,
		"first_name": user.first_name,
		"last_name": user.last_name,
		"full_name": user.full_name,
		"email": user.email,
		"user_image": user.user_image,
		"roles": user.roles,
		"brand_image": frappe.get_single_value("Website Settings", "banner_image"),
		"language": user.language,
	}


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


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_enabled_languages():
	languages = frappe.get_all(
		"Language",
		filters={"enabled": 1},
		fields=["name", "language_name", "language_code"],
		order_by="language_name",
	)
	return languages


@frappe.whitelist()
def update_user_language(language_code: str):
	if not frappe.db.exists("Language", {"language_code": language_code}):
		frappe.throw(_("Invalid language"))

	frappe.db.set_value("User", frappe.session.user, "language", language_code)


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def get_translations():
	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("System Settings", "language")

	return get_all_translations(language)


def has_app_permission():
	return True


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def validate_coupon(coupon_code: str, event: str, user_email: str | None = None) -> dict:
	if not frappe.db.exists("Buzz Coupon Code", coupon_code):
		return {"valid": False, "error": _("Invalid coupon code")}

	coupon = frappe.get_doc("Buzz Coupon Code", coupon_code)

	is_valid, error = coupon.is_valid_for_event(event)
	if not is_valid:
		return {"valid": False, "error": error}

	is_available, error = coupon.is_usage_available()
	if not is_available:
		return {"valid": False, "error": error}

	if frappe.session.user == "Guest":
		check_user = user_email.lower().strip() if user_email else None
	else:
		check_user = frappe.session.user
	is_limited, error = coupon.is_user_limit_reached(user=check_user)
	if is_limited:
		return {"valid": False, "error": error}

	if coupon.coupon_type == "Discount":
		return {
			"valid": True,
			"coupon_type": "Discount",
			"discount_type": coupon.discount_type,
			"discount_value": coupon.discount_value,
			"max_discount_amount": coupon.maximum_discount_amount or 0,
			"min_order_value": coupon.minimum_order_value or 0,
		}

	remaining = coupon.number_of_free_tickets - coupon.free_tickets_claimed
	if remaining <= 0:
		return {"valid": False, "error": _("All free tickets have been claimed")}

	return {
		"valid": True,
		"coupon_type": "Free Tickets",
		"ticket_type": coupon.ticket_type,
		"remaining_tickets": remaining,
		"free_add_ons": [a.add_on for a in coupon.free_add_ons],
	}


@frappe.whitelist()
def get_campaign_details(campaign: str):
	if not frappe.db.exists("Buzz Campaign", campaign):
		frappe.throw(_("Campaign not found"), frappe.DoesNotExistError)

	campaign_doc = frappe.get_cached_doc("Buzz Campaign", campaign)

	if not campaign_doc.enabled:
		frappe.throw(_("This campaign is not active"))

	return {
		"title": campaign_doc.title,
		"description": campaign_doc.description,
		"event": campaign_doc.event,
	}


@frappe.whitelist()
def register_campaign_interest(campaign: str):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to register your interest"))

	if not is_app_installed("crm"):
		frappe.throw(_("CRM integration is not available"))

	if not frappe.db.exists("Buzz Campaign", campaign):
		frappe.throw(_("Campaign not found"), frappe.DoesNotExistError)

	campaign_doc = frappe.get_cached_doc("Buzz Campaign", campaign)

	user = frappe.get_cached_doc("User", frappe.session.user)
	first_name = user.first_name or user.full_name or frappe.session.user.split("@")[0]

	existing_lead = frappe.db.exists(
		"CRM Lead",
		{"email": frappe.session.user, "buzz_campaign": campaign},
	)
	if existing_lead:
		frappe.throw(_("You have already registered for this campaign"))

	ticket = None
	if campaign_doc.event:
		ticket = frappe.db.get_value(
			"Event Ticket",
			{
				"attendee_email": frappe.session.user,
				"event": campaign_doc.event,
				"docstatus": 1,
			},
			"name",
		)

	lead = frappe.get_doc(
		{
			"doctype": "CRM Lead",
			"first_name": first_name,
			"email": frappe.session.user,
			"status": "New",
			"buzz_campaign": campaign,
			"event_ticket": ticket,
		}
	)
	lead.insert(ignore_permissions=True)
