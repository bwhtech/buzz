from frappe import _lt

from buzz.api.exceptions import Conflict, ResourceNotFound


class TicketNotFound(ResourceNotFound):
	title = _lt("Ticket Not Found")
	message = _lt("No ticket matches this code.")


class TicketCancelled(Conflict):
	title = _lt("Ticket Cancelled")
	message = _lt("This ticket has been cancelled and cannot be checked in.")


class AlreadyCheckedIn(Conflict):
	title = _lt("Already Checked In")
	message = _lt("This ticket was already checked in today, at {checked_in_at}.")
