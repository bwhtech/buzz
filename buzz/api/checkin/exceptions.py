from frappe import _lt

from buzz.api.exceptions import Conflict, ResourceNotFound


class TicketNotFound(ResourceNotFound):
	title = _lt("Ticket Not Found")
	message = _lt("No ticket matches this code.")


class TicketCancelled(Conflict):
	title = _lt("Ticket Cancelled")
	message = _lt("This ticket has been cancelled and cannot be checked in.")


class TicketRefunded(Conflict):
	title = _lt("Ticket Refunded")
	message = _lt("This ticket has been refunded and cannot be checked in.")


class AlreadyCheckedIn(Conflict):
	title = _lt("Already Checked In")
	message = _lt("This ticket was already checked in at {zone}, on {checked_in_at}.")


class NotCheckedIn(Conflict):
	title = _lt("Not Checked In")
	message = _lt("This ticket has not been checked in at {zone}.")


class NotAllowedInZone(Conflict):
	title = _lt("Not Allowed Here")
	message = _lt("This ticket type does not give access to {zone}.")
