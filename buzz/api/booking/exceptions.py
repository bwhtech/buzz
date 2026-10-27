from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, Conflict, NotPermitted


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


class AddOnNotForEvent(BuzzAPIError):
	title = _lt("Add-on Unavailable")
	message = _lt("This add-on is not available for this event.")


class InvalidAddOnValue(BuzzAPIError):
	title = _lt("Invalid Option")
	message = _lt("{value} is not a valid option for this add-on.")


class TicketsUnavailable(Conflict):
	title = _lt("Tickets Unavailable")
	message = _lt("Only {remaining} {ticket_type} tickets are left.")


class TooManyTicketsHeld(BuzzAPIError):
	http_status_code = 429
	title = _lt("Too Many Tickets Held")
	message = _lt("You can hold at most {limit} tickets at a time.")


class InvoiceDetailsMissing(BuzzAPIError):
	title = _lt("Invoice Details Missing")
	message = _lt("A tax invoice needs your tax ID and business name.")


class InvalidCoupon(BuzzAPIError):
	title = _lt("Invalid Code")
	message = _lt("Invalid or expired code")


class ApprovalNeedsFreeTickets(BuzzAPIError):
	title = _lt("Approval Needs Free Tickets")
	message = _lt("Approval only works with free tickets. Turn off approval first.")


class ApprovalRequestPending(Conflict):
	title = _lt("Request Pending")
	message = _lt("You already have a request pending for this event")


class BookingNotPending(Conflict):
	title = _lt("Request Not Pending")
	message = _lt("This request is no longer waiting for approval.")


class CannotWithdrawBooking(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You cannot withdraw this request.")
