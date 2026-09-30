from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, NotPermitted


class PlaceSearchNotEnabled(BuzzAPIError):
	title = _lt("Place Search Not Available")
	message = _lt("Google Maps place search is not set up on this site.")


class PlaceSearchFailed(BuzzAPIError):
	title = _lt("Place Search Failed")
	message = _lt("Google Maps could not be reached. Add the venue manually instead.")


class CannotAddVenues(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You cannot add venues.")
