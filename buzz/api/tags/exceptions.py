from frappe import _lt

from buzz.api.exceptions import BuzzAPIError


class NotTaggable(BuzzAPIError):
	title = _lt("Cannot Tag")
	message = _lt("These records cannot be tagged.")


class EmptyTagLabel(BuzzAPIError):
	title = _lt("Name Required")
	message = _lt("Give the tag a name.")
