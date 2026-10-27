import hashlib
import hmac
from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.utils import (
	cstr,
	get_fullname,
	validate_email_address,
	validate_phone_number_with_country_code,
)
from frappe.utils.password import get_encryption_key

from buzz.api.booking.exceptions import (
	AddOnNotForEvent,
	InvalidAddOnValue,
	InvalidCoupon,
	InvoiceDetailsMissing,
	RegistrationsClosed,
)
from buzz.api.booking.guests import get_or_create_guest_user, verify_guest_otp
from buzz.api.booking.schemas import (
	BookingRequest,
	FreeBookingResponse,
	OfflineBookingResponse,
	PaymentLinkResponse,
)
from buzz.api.filters.conditions import form_questions
from buzz.api.forms.answers import CustomAnswers
from buzz.events.doctype.buzz_form.form_types import (
	ATTENDEE_FORM_DOCTYPE,
	REGISTRATION_FORM_DOCTYPE,
	is_registration_closed,
)
from buzz.payments import get_payment_link_for_booking
from buzz.ticketing.doctype.buzz_coupon_code.buzz_coupon_code import BuzzCouponCode
from buzz.ticketing.doctype.event_ticket_type.event_ticket_type import (
	default_currency,
	start_capacity_transaction,
)
from buzz.utils import ZOOM_BACKED_CATEGORIES

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
		start_capacity_transaction()
		self.validate_event()
		self.validate_offline_currency()
		self.validate_answers()
		self.validate_add_ons()
		booking = self.build_booking()
		booking.insert(ignore_permissions=True)
		frappe.db.commit()  # nosemgrep: frappe-manual-commit
		return self.finalize(booking)

	def validate_offline_currency(self) -> None:
		currency = self.request.currency
		if self.request.is_offline and currency and currency != default_currency(self.request.event):
			frappe.throw(_("Offline payment isn't available when paying in {0}").format(currency))

	def validate_event(self) -> None:
		if not self.event.is_published:
			frappe.throw(_("Event is not live"))
		if are_registrations_closed(self.event):
			RegistrationsClosed.throw()

	def validate_answers(self) -> None:
		"""Check every registration answer, booking- and attendee-level, before anything with
		a side effect runs.

		verify_guest_otp deletes the code from the cache, and no rollback puts it back, so an
		answer rejected later in build_booking would cost the guest a fresh OTP.
		"""
		event = self.request.event
		booking_questions = form_questions(event, REGISTRATION_FORM_DOCTYPE)
		attendee_questions = form_questions(event, ATTENDEE_FORM_DOCTYPE)
		self.booking_answers = self.answer_rows(booking_questions, self.request.booking_custom_fields)
		self.attendee_answers = [
			self.answer_rows(
				attendee_questions,
				attendee.get("custom_fields"),
				{"ticket_type": cstr(attendee.get("ticket_type"))},
			)
			for attendee in self.request.attendees
		]

	def answer_rows(self, questions: list, values: dict | None, context: dict | None = None) -> list[dict]:
		return CustomAnswers(questions).rows(values or {}, context)

	def validate_add_ons(self) -> None:
		"""Every add-on named in the request must be an enabled add-on of this event, and
		its value one of the add-on's options. Runs before build_booking so a bad selection
		is rejected before any document is written."""
		allowed = self.allowed_add_ons()
		for attendee in self.request.attendees:
			for add_on in attendee.get("add_ons") or []:
				catalog = allowed.get(add_on["add_on"])
				if not catalog:
					AddOnNotForEvent.throw()
				if catalog.user_selects_option:
					options = (catalog.options or "").split("\n")
					if add_on.get("value") not in options:
						InvalidAddOnValue.throw(value=add_on.get("value"))

	def allowed_add_ons(self) -> dict:
		rows = frappe.db.get_all(
			"Ticket Add-on",
			filters={"event": self.request.event, "enabled": 1},
			fields=["name", "options", "user_selects_option"],
		)
		return {row.name: row for row in rows}

	def build_booking(self) -> "EventBooking":
		booking = frappe.new_doc("Event Booking")
		booking.event = self.request.event
		booking.coupon_code = self.resolve_coupon()
		booking.currency = self.request.currency
		booking.hold_token = self.request.hold_token
		booking.user = self.resolve_user()
		self.apply_buyer_details(booking)
		self.apply_invoice_details(booking)
		self.append_utm_parameters(booking)
		self.append_custom_fields(booking)
		self.append_attendees(booking)
		return booking

	def resolve_coupon(self) -> str | None:
		if not self.request.coupon_code:
			return None
		coupon = BuzzCouponCode.find_promo(self.request.event, self.request.coupon_code)
		if not coupon:
			InvalidCoupon.throw()
		return coupon.name

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

	# Who pays and receives the confirmation; falls back to the guest contact or the booking user.
	def apply_buyer_details(self, booking: "EventBooking") -> None:
		request = self.request
		booking.buyer_email = (
			request.buyer_email or request.guest_email or frappe.db.get_value("User", booking.user, "email")
		)
		booking.buyer_name = request.buyer_name or request.guest_full_name or get_fullname(booking.user)
		booking.buyer_phone = request.buyer_phone or request.guest_phone
		if booking.buyer_email:
			validate_email_address(booking.buyer_email, throw=True)
		if booking.buyer_phone:
			validate_phone_number_with_country_code(booking.buyer_phone, _("Phone Number"))

	def apply_invoice_details(self, booking: "EventBooking") -> None:
		if not (self.event.apply_tax and self.request.invoice_requested):
			return
		if not (self.request.tax_id and self.request.business_name):
			InvoiceDetailsMissing.throw()
		booking.update(
			{
				"invoice_requested": 1,
				"tax_id": self.request.tax_id,
				"business_name": self.request.business_name,
				"billing_address": self.request.billing_address,
				"billing_state": self.request.billing_state,
			}
		)

	def append_utm_parameters(self, booking: "EventBooking") -> None:
		for utm_parameter in self.request.utm_parameters or []:
			booking.append(
				"utm_parameters",
				{"utm_name": utm_parameter.get("utm_name"), "value": utm_parameter.get("value")},
			)

	def append_custom_fields(self, booking: "EventBooking") -> None:
		for answer in self.booking_answers:
			booking.append("additional_fields", answer)

	def append_attendees(self, booking: "EventBooking") -> None:
		self.validate_zoom_last_names()
		for attendee, answers in zip(self.request.attendees, self.attendee_answers, strict=True):
			booking.append("attendees", self.attendee_row(attendee, answers))

	def validate_zoom_last_names(self) -> None:
		if self.event.category not in ZOOM_BACKED_CATEGORIES:
			return
		for attendee in self.request.attendees:
			if not (attendee.get("last_name") or "").strip():
				frappe.throw(_("Last name is required for all attendees in Zoom events"))

	def attendee_row(self, attendee: dict, answers: list[dict]) -> dict:
		first_name, last_name = resolve_attendee_names(attendee)

		add_ons = attendee.get("add_ons", None)
		if add_ons:
			add_ons = create_add_on_doc(f"{first_name} {last_name}".strip(), add_ons)

		custom_fields = {
			answer["fieldname"]: (attendee.get("custom_fields") or {})[answer["fieldname"]]
			for answer in answers
		}

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
		booking.hold_until_approval()
		self.attach_payment_proof(booking)
		self.acknowledge_offline_booking(booking)
		return OfflineBookingResponse(booking_name=booking.name, offline_payment=True)

	def acknowledge_offline_booking(self, booking: "EventBooking") -> None:
		"""The booking is only a draft until an approval verifies the payment, so this
		acknowledgement is the booker's only receipt until then."""
		try:
			booking.send_offline_acknowledgement_email()
		except Exception:
			frappe.log_error(
				title="Offline booking acknowledgement email failed",
				reference_doctype=booking.doctype,
				reference_name=booking.name,
			)

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
	form = frappe.db.get_value(
		"Buzz Form",
		{"event": event_doc.name, "form_doctype": REGISTRATION_FORM_DOCTYPE},
		["publish", "auto_close_at"],
		as_dict=True,
	)
	return is_registration_closed(form, event_doc)


def resolve_attendee_names(attendee: dict) -> tuple[str, str]:
	first_name = (attendee.get("first_name") or "").strip()
	last_name = (attendee.get("last_name") or "").strip()

	if not first_name and attendee.get("full_name"):
		name_parts = attendee["full_name"].strip().split(" ", 1)
		first_name = name_parts[0]
		last_name = last_name or (name_parts[1] if len(name_parts) > 1 else "")

	return first_name, last_name


def create_add_on_doc(attendee_name: str, add_ons: list[dict]):
	# Price and currency are read from the catalog and overwrite whatever the request
	# carried. The Ticket Add-on Value price field only fetches when left empty, so a
	# price sent in the payload would otherwise be charged as-is.
	for add_on in add_ons:
		price, currency = frappe.db.get_value("Ticket Add-on", add_on["add_on"], ["price", "currency"])
		add_on["price"] = price
		add_on["currency"] = currency

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
