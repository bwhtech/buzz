from typing import NoReturn

import frappe
from frappe import _lt


class BuzzAPIError(frappe.ValidationError):
	"""Base for API errors.

	`http_status_code` is read by frappe.app.handle_exception. `title` and `message` are
	declared with `_lt` so they are translated per request rather than at import, and reach
	the dashboard as `_server_messages`, which is what `err.messages[0]` renders.

	Raise via `throw()`, never `raise SomeError` — a bare raise skips msgprint, leaving the
	dashboard to fall back to "Internal Server Error".
	"""

	http_status_code = 400
	title = _lt("Error")
	message = _lt("Something went wrong. Please try again.")

	@classmethod
	def throw(cls, **context) -> NoReturn:
		message = str(cls.message)
		frappe.throw(message.format(**context) if context else message, cls, title=str(cls.title))


class ResourceNotFound(BuzzAPIError):
	http_status_code = 404
	title = _lt("Not Found")
	message = _lt("The record you are looking for does not exist.")


class NotPermitted(BuzzAPIError):
	http_status_code = 403
	title = _lt("Not Permitted")
	message = _lt("You do not have permission to do this.")


class Conflict(BuzzAPIError):
	http_status_code = 409
	title = _lt("Not Allowed")
	message = _lt("This action conflicts with the current state of the record.")
