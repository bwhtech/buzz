from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, Conflict


class TooManyOTPAttempts(BuzzAPIError):
	# The dashboard closes the OTP modal on the "Too many" fragment; keep it.
	http_status_code = 429
	title = _lt("Too Many Attempts")
	message = _lt("Too many failed attempts. Please try again later.")


class OTPExpired(BuzzAPIError):
	# The dashboard closes the OTP modal on the "expired" fragment; keep it.
	title = _lt("Code Expired")
	message = _lt("Verification code expired. Please request a new one.")


class InvalidOTP(BuzzAPIError):
	title = _lt("Invalid Code")
	message = _lt("Invalid verification code")


class RegistrationsClosed(Conflict):
	title = _lt("Registrations Closed")
	message = _lt("Registrations for this event are closed")
