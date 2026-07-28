import frappe


class BuzzAPIError(frappe.ValidationError):
	# frappe.app.handle_exception reads http_status_code off the exception.
	http_status_code = 400


class ResourceNotFound(BuzzAPIError):
	http_status_code = 404


class NotPermitted(BuzzAPIError):
	http_status_code = 403


class Conflict(BuzzAPIError):
	http_status_code = 409
