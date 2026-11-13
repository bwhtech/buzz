from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, Conflict, ResourceNotFound


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


class AddOnNotForTicketType(BuzzAPIError):
	title = _lt("Add-on Unavailable")
	message = _lt("This add-on is not available for the selected ticket type.")


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


class TooManyTicketsInBooking(BuzzAPIError):
	title = _lt("Too Many Tickets")
	message = _lt("You can book at most {limit} tickets at a time.")


class InvoiceDetailsMissing(BuzzAPIError):
	title = _lt("Invoice Details Missing")
	message = _lt("A tax invoice needs your tax ID and business name.")


class InvoiceUnavailable(ResourceNotFound):
	title = _lt("Invoice Unavailable")
	message = _lt("This booking has no invoice.")


class InvalidCoupon(BuzzAPIError):
	title = _lt("Invalid Code")
	message = _lt("Invalid or expired code")


class InvalidAccessCode(BuzzAPIError):
	title = _lt("Invalid Access Code")
	message = _lt("This access code is not valid.")


class HiddenTicketType(BuzzAPIError):
	title = _lt("Tickets Unavailable")
	message = _lt("These tickets are only available with a valid access code.")


class RequestAlreadyOpen(Conflict):
	title = _lt("Request Already Open")
	message = _lt("You already have an open request for this event.")


class RequestNotOpen(Conflict):
	title = _lt("Request Not Open")
	message = _lt("This request is no longer open.")


class InviteNotFound(ResourceNotFound):
	title = _lt("Invite Not Found")
	message = _lt("This invite link isn't valid.")


class InviteNotOpen(Conflict):
	title = _lt("Invite Closed")
	message = _lt("This invite has already been answered or withdrawn.")


class InviteExpired(Conflict):
	title = _lt("Event Over")
	message = _lt("This event has already ended.")


class TooManyInvites(BuzzAPIError):
	title = _lt("Too Many Guests")
	message = _lt("Invite at most {limit} guests at a time.")
