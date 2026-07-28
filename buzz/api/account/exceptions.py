from frappe import _lt

from buzz.api.exceptions import BuzzAPIError


class UnknownLanguage(BuzzAPIError):
	title = _lt("Language Not Available")
	message = _lt("{language_code} is not one of the languages enabled for this site.")
