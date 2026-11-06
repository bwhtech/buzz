from frappe import _lt

from buzz.api.exceptions import NotPermitted


class NotAnIntegration(NotPermitted):
	message = _lt("This account is not the integration of exactly one team.")
