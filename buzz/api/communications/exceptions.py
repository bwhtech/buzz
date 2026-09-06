from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, NotPermitted


class NoRecipients(BuzzAPIError):
	title = _lt("Nobody To Send To")
	message = _lt("No one matches these recipients yet.")


class CannotSendCommunication(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You cannot send messages for this event.")


class UnknownAudience(BuzzAPIError):
	title = _lt("Unknown Audience")
	message = _lt("{audience} is not an audience. Choose Guests or Speakers.")
