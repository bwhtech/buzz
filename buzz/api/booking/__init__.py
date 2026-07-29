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
from frappe.utils import (
	get_datetime,
	get_datetime_in_timezone,
	get_system_timezone,
	validate_email_address,
)
from frappe.utils.password import get_encryption_key

from buzz.api.tickets import windows
from buzz.api.tickets.services import create_add_on_doc
from buzz.payments import get_payment_gateways_for_event, get_payment_link_for_booking
from buzz.utils import ZOOM_BACKED_CATEGORIES, build_event_datetimes

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


def are_registrations_closed(event_doc) -> bool:
	event_timezone = event_doc.time_zone or get_system_timezone()
	current_datetime_in_event_timezone = get_datetime_in_timezone(event_timezone).replace(tzinfo=None)

	if event_doc.registrations_close_at:
		return current_datetime_in_event_timezone > get_datetime(event_doc.registrations_close_at)

	# No explicit cutoff set - registrations close once the event itself has ended.
	_, event_end_datetime = build_event_datetimes(event_doc)
	return current_datetime_in_event_timezone > event_end_datetime


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
			"time_zone_label": event_doc.time_zone_label,
			"venue": event_doc.venue,
			"medium": event_doc.medium,
			"category": event_doc.category,
			"banner_image": event_doc.banner_image,
			"short_description": event_doc.short_description,
			"free_event": event_doc.free_event,
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

	if event_doc.category in ZOOM_BACKED_CATEGORIES:
		for attendee in attendees:
			if not (attendee.get("last_name") or "").strip():
				frappe.throw(_("Last name is required for all attendees in Zoom events"))

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
	frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit

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
			redirect_to=f"/b/booking-success/{booking.name}?token={get_booking_access_token(booking.name)}",
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
				"free_event": event_doc.get("free_event"),
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

	event_id = details.event.name
	details.can_transfer_ticket = windows.is_window_open(event_id, windows.TRANSFER)
	details.can_change_add_ons = windows.is_window_open(event_id, windows.ADD_ON_CHANGE)
	details.can_request_cancellation = windows.is_window_open(event_id, windows.CANCELLATION)

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
