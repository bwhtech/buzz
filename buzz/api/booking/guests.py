import os
from base64 import b32encode

import frappe
import pyotp
from frappe import _
from frappe.auth import LoginAttemptTracker
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.utils import validate_email_address

from buzz.api.booking.exceptions import InvalidOTP, OTPExpired, TooManyOTPAttempts


def send_booking_otp(event: int, identifier: str) -> dict | None:
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

	deliver_otp(channel, identifier, otp_code)
	frappe.cache.set_value(cache_key, otp_secret, expires_in_sec=600)


def deliver_otp(channel: str, identifier: str, otp_code: str) -> None:
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


def verify_guest_otp(channel: str, identifier: str, otp: str) -> None:
	cache_key = f"guest_booking_otp:{channel}:{identifier}"
	tracker = LoginAttemptTracker(
		key=f"guest_otp:{channel}:{identifier}",
		max_consecutive_login_attempts=5,
		lock_interval=600,
	)

	if not tracker.is_user_allowed():
		TooManyOTPAttempts.throw()

	otp_secret = frappe.cache.get_value(cache_key)
	if not otp_secret:
		OTPExpired.throw()

	if not pyotp.HOTP(otp_secret).verify(otp.strip(), 0):
		tracker.add_failure_attempt()
		InvalidOTP.throw()

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
