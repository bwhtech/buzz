from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, Conflict


class InvalidUsername(BuzzAPIError):
	title = _lt("Invalid Username")
	message = _lt("Use 3 to 30 lowercase letters, numbers, dots, dashes or underscores.")


class UsernameTaken(Conflict):
	title = _lt("Username Taken")
	message = _lt("{username} is already taken. Try another one.")
