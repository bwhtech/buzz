from frappe import _lt

from buzz.api.exceptions import BuzzAPIError


class InvalidFilter(BuzzAPIError):
	title = _lt("Invalid Filter")
	message = _lt("One of the filters is not valid for this list.")
