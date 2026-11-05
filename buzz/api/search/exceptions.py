from frappe import _lt

from buzz.api.exceptions import BuzzAPIError


class UnknownSearchSection(BuzzAPIError):
	title = _lt("Unknown Section")
	message = _lt("{section} is not a section of an event.")
