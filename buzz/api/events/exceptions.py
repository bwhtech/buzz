from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, NotPermitted


class CannotCreateEvents(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You cannot create events for this team.")


class ZoomNotAvailable(BuzzAPIError):
	title = _lt("Zoom Not Available")
	message = _lt("Zoom is not set up on this site, so a Zoom meeting cannot be created.")
