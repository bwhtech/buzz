import hashlib
import hmac
from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import (
	get_datetime,
	get_datetime_in_timezone,
	get_system_timezone,
	validate_email_address,
	validate_phone_number_with_country_code,
)
from frappe.utils.password import get_encryption_key

from buzz.api.booking.exceptions import RegistrationsClosed
from buzz.api.booking.guests import get_or_create_guest_user, verify_guest_otp
from buzz.api.booking.schemas import (
	BookingRequest,
	FreeBookingResponse,
	OfflineBookingResponse,
	PaymentLinkResponse,
)
from buzz.payments import get_payment_link_for_booking
from buzz.utils import ZOOM_BACKED_CATEGORIES, build_event_datetimes

if TYPE_CHECKING:
	from buzz.events.doctype.buzz_event.buzz_event import BuzzEvent
	from buzz.ticketing.doctype.event_booking.event_booking import EventBooking

OFFLINE_PAYMENT_METHOD = "Offline"


class BookingService:
	"""Create an Event Booking from a validated request and hand back the next step."""

	def __init__(self, request: BookingRequest):
		self.request = request

	@property
	def event(self) -> "BuzzEvent":
		return frappe.get_cached_doc("Buzz Event", self.request.event)

	def process(self) -> FreeBookingResponse | OfflineBookingResponse | PaymentLinkResponse:
		self.validate_event()
		self.validate_phone_fields()
		booking = self.build_booking()
		booking.insert(ignore_permissions=True)
		frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit
		return self.finalize(booking)

	def validate_event(self) -> None:
		if not self.event.is_published:
			frappe.throw(_("Event is not live"))
		if are_registrations_closed(self.event):
			RegistrationsClosed.throw()

	def validate_phone_fields(self) -> None:
		"""Validate every Phone custom field, booking-level and attendee-level, before
		anything with a side effect runs.

		verify_guest_otp deletes the code from the cache, and no rollback puts it back, so a
		phone rejected later in build_booking would cost the guest a fresh OTP.
		"""
		phone_field_map = self.phone_field_labels()
		validate_custom_fields(self.request.booking_custom_fields or {}, phone_field_map)
		for attendee in self.request.attendees:
			validate_custom_fields(attendee.get("custom_fields") or {}, phone_field_map)

	def build_booking(self) -> "EventBooking":
		booking = frappe.new_doc("Event Booking")
		booking.event = self.request.event
		booking.coupon_code = self.request.coupon_code
		booking.user = self.resolve_user()
		self.apply_invoice_details(booking)
		self.append_utm_parameters(booking)
		self.append_custom_fields(booking)
		self.append_attendees(booking)
		return booking

	def resolve_user(self) -> str:
		if frappe.session.user != "Guest":
			return frappe.session.user
		return self.resolve_guest_user()

	def resolve_guest_user(self) -> str:
		if not self.event.allow_guest_booking:
			frappe.throw(_("Please log in to access this feature"), frappe.AuthenticationError)
		if not self.request.guest_email:
			frappe.throw(_("Email is required for guest booking"))
		validate_email_address(self.request.guest_email, throw=True)
		self.verify_guest()
		return get_or_create_guest_user(self.request.guest_email, self.guest_full_name())

	def verify_guest(self) -> None:
		method = self.event.guest_verification_method
		if method not in ("Email OTP", "Phone OTP"):
			return
		if not self.request.otp:
			frappe.throw(_("Verification code is required"))
		if method == "Email OTP":
			verify_guest_otp("email", self.request.guest_email.lower().strip(), self.request.otp)
			return
		if not self.request.guest_phone:
			frappe.throw(_("Phone number is required"))
		guest_phone = self.request.guest_phone.strip()
		validate_phone_number_with_country_code(guest_phone, _("Phone Number"))
		verify_guest_otp("phone", guest_phone, self.request.otp)

	def guest_full_name(self) -> str:
		first_name = (self.request.attendees[0].get("first_name") or "").strip()
		last_name = (self.request.attendees[0].get("last_name") or "").strip()
		full_name = (self.request.guest_full_name or "").strip() or f"{first_name} {last_name}".strip()
		if not full_name:
			frappe.throw(_("Full name is required for guest booking"))
		return full_name

	def apply_invoice_details(self, booking: "EventBooking") -> None:
		if not (self.event.apply_tax and self.request.invoice_requested):
			return
		booking.invoice_requested = 1
		booking.tax_id = self.request.tax_id
		booking.billing_address = self.request.billing_address

	def append_utm_parameters(self, booking: "EventBooking") -> None:
		for utm_parameter in self.request.utm_parameters or []:
			booking.append(
				"utm_parameters",
				{"utm_name": utm_parameter.get("utm_name"), "value": utm_parameter.get("value")},
			)

	def append_custom_fields(self, booking: "EventBooking") -> None:
		if not self.request.booking_custom_fields:
			return
		definitions = frappe.db.get_all(
			"Buzz Custom Field",
			filters={"event": self.request.event, "enabled": 1, "applied_to": "Booking"},
			fields=["fieldname", "label", "fieldtype"],
		)
		definition_map = {definition["fieldname"]: definition for definition in definitions}

		for field_name, field_value in self.request.booking_custom_fields.items():
			if field_value and field_name in definition_map:
				definition = definition_map[field_name]
				booking.append(
					"additional_fields",
					{
						"fieldname": field_name,
						"value": str(field_value),
						"label": definition["label"],
						"fieldtype": definition["fieldtype"],
					},
				)

	def append_attendees(self, booking: "EventBooking") -> None:
		self.validate_zoom_last_names()
		for attendee in self.request.attendees:
			booking.append("attendees", self.attendee_row(attendee))

	def validate_zoom_last_names(self) -> None:
		if self.event.category not in ZOOM_BACKED_CATEGORIES:
			return
		for attendee in self.request.attendees:
			if not (attendee.get("last_name") or "").strip():
				frappe.throw(_("Last name is required for all attendees in Zoom events"))

	def phone_field_labels(self) -> dict:
		"""Label by fieldname for every Phone custom field on the event, booking- and
		attendee-level alike, so `applied_to` is deliberately not filtered on."""
		phone_fields = frappe.db.get_all(
			"Buzz Custom Field",
			filters={"event": self.request.event, "enabled": 1, "fieldtype": "Phone"},
			fields=["fieldname", "label"],
		)
		return {field.fieldname: field.label for field in phone_fields}

	def attendee_row(self, attendee: dict) -> dict:
		first_name, last_name = resolve_attendee_names(attendee)

		add_ons = attendee.get("add_ons", None)
		if add_ons:
			add_ons = create_add_on_doc(f"{first_name} {last_name}".strip(), add_ons)

		custom_fields = attendee.get("custom_fields", {})

		return {
			"first_name": first_name,
			"last_name": last_name,
			"email": attendee.get("email"),
			"ticket_type": attendee.get("ticket_type"),
			"add_ons": add_ons.name if add_ons else None,
			"custom_fields": custom_fields if custom_fields else None,
		}

	def finalize(
		self, booking: "EventBooking"
	) -> FreeBookingResponse | OfflineBookingResponse | PaymentLinkResponse:
		if booking.total_amount == 0:
			return self.free_booking_response(booking)
		if self.request.is_offline:
			return self.offline_booking_response(booking)
		return self.payment_link_response(booking)

	def free_booking_response(self, booking: "EventBooking") -> FreeBookingResponse:
		booking.flags.ignore_permissions = True
		booking.submit()
		return FreeBookingResponse(
			booking_name=booking.name,
			redirect_to=f"/booking-success/{booking.name}?token={get_booking_access_token(booking.name)}",
		)

	def offline_booking_response(self, booking: "EventBooking") -> OfflineBookingResponse:
		method = self.offline_method()
		booking.payment_method = OFFLINE_PAYMENT_METHOD
		booking.offline_payment_method = method.title
		booking.status = "Approval Pending"
		booking.payment_status = "Verification Pending"
		booking.flags.ignore_permissions = True
		booking.save()
		self.attach_payment_proof(booking)
		return OfflineBookingResponse(booking_name=booking.name, offline_payment=True)

	def offline_method(self) -> dict:
		filters = {"event": self.request.event, "enabled": 1}
		if self.request.offline_payment_method:
			filters["name"] = self.request.offline_payment_method
		method = frappe.db.get_value("Offline Payment Method", filters, ["name", "title"], as_dict=True)
		if not method:
			frappe.throw(_("Offline payment is not enabled for this event"))
		return method

	def attach_payment_proof(self, booking: "EventBooking") -> None:
		if not self.request.payment_proof:
			return
		try:
			frappe.get_doc(
				{
					"doctype": "File",
					"file_url": self.request.payment_proof,
					"attached_to_doctype": "Event Booking",
					"attached_to_name": booking.name,
					"is_private": 1,
				}
			).insert(ignore_permissions=True)
		except Exception as exception:
			frappe.log_error(f"Failed to attach payment proof: {exception}")

	def payment_link_response(self, booking: "EventBooking") -> PaymentLinkResponse:
		return PaymentLinkResponse(
			payment_link=get_payment_link_for_booking(
				booking.name,
				redirect_to=f"/b/booking-success/{booking.name}?token={get_booking_access_token(booking.name)}",
				payment_gateway=self.request.payment_gateway,
			)
		)


def are_registrations_closed(event_doc) -> bool:
	event_timezone = event_doc.time_zone or get_system_timezone()
	current_datetime_in_event_timezone = get_datetime_in_timezone(event_timezone).replace(tzinfo=None)

	if event_doc.registrations_close_at:
		return current_datetime_in_event_timezone > get_datetime(event_doc.registrations_close_at)

	# No explicit cutoff set - registrations close once the event itself has ended.
	_event_start_datetime, event_end_datetime = build_event_datetimes(event_doc)
	return current_datetime_in_event_timezone > event_end_datetime


def resolve_attendee_names(attendee: dict) -> tuple[str, str]:
	first_name = (attendee.get("first_name") or "").strip()
	last_name = (attendee.get("last_name") or "").strip()

	if not first_name and attendee.get("full_name"):
		name_parts = attendee["full_name"].strip().split(" ", 1)
		first_name = name_parts[0]
		last_name = last_name or (name_parts[1] if len(name_parts) > 1 else "")

	return first_name, last_name


def validate_custom_fields(custom_fields_data: dict, phone_field_map: dict) -> None:
	for field_name, field_value in custom_fields_data.items():
		if field_value and field_name in phone_field_map:
			validate_phone_number_with_country_code(str(field_value), phone_field_map[field_name])


def create_add_on_doc(attendee_name: str, add_ons: list[dict]):
	for add_on in add_ons:
		add_on["currency"] = frappe.db.get_value("Ticket Add-on", add_on["add_on"], "currency")

	return frappe.get_doc(
		{"doctype": "Attendee Ticket Add-on", "add_ons": add_ons, "attendee_name": attendee_name}
	).insert(ignore_permissions=True)


def get_booking_access_token(booking_name: str) -> str:
	"""HMAC of the booking name signed with the site encryption_key.

	Lets a guest (whose browser session stays "Guest") open their own booking
	confirmation without logging in, while keeping sequential booking names
	unguessable (no IDOR)."""
	key = get_encryption_key().encode()
	return hmac.new(key, booking_name.encode(), hashlib.sha256).hexdigest()


def verify_booking_access_token(booking_name: str, token: str | None) -> bool:
	return bool(token) and hmac.compare_digest(get_booking_access_token(booking_name), token)
