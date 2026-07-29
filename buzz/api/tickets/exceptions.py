from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, Conflict, NotPermitted, ResourceNotFound


class TicketNotFound(ResourceNotFound):
	title = _lt("Ticket Not Found")
	message = _lt("Ticket not found.")


class AddOnValueNotFound(ResourceNotFound):
	title = _lt("Add-on Not Found")
	message = _lt("Add-on value not found.")


class TicketNotAccessible(NotPermitted):
	message = _lt("You are not permitted to view this ticket.")


class TransferNotPermitted(NotPermitted):
	message = _lt("You are not permitted to transfer this ticket.")


class CancellationNotPermitted(NotPermitted):
	message = _lt("You are not permitted to request cancellation for this booking.")


class TransferWindowClosed(Conflict):
	title = _lt("Transfers Closed")
	message = _lt("The transfer window for this event has closed.")


class AddOnChangeWindowClosed(Conflict):
	title = _lt("Changes Closed")
	message = _lt("The add-on change window has closed as the event is approaching.")


class CancellationWindowClosed(Conflict):
	title = _lt("Cancellations Closed")
	message = _lt("Cancellation requests are no longer allowed for this event.")


class CancellationAlreadyRequested(Conflict):
	title = _lt("Already Requested")
	message = _lt("A cancellation request already exists for this booking.")


class TicketNotInBooking(BuzzAPIError):
	title = _lt("Wrong Booking")
	message = _lt("Ticket {ticket_id} does not belong to booking {booking_id}.")
