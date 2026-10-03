from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, NotPermitted, ResourceNotFound


class EventNotFound(ResourceNotFound):
	title = _lt("Event Not Found")
	message = _lt("This event does not exist.")


class CannotManageEvent(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You cannot manage this event.")


class CannotCreateEvents(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You cannot create events for this team.")


class ZoomNotAvailable(BuzzAPIError):
	title = _lt("Zoom Not Available")
	message = _lt("Zoom is not set up on this site, so a Zoom meeting cannot be created.")


class EventEnded(BuzzAPIError):
	title = _lt("Event Has Ended")
	message = _lt("You cannot convert events that have ended to Zoom meetings.")


class TaxDetailsMissing(BuzzAPIError):
	title = _lt("Tax Details Missing")
	message = _lt("Add your team's tax details before charging tax on tickets.")
