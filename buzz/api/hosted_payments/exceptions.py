from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, ResourceNotFound


class ForeignSiteURL(BuzzAPIError):
	title = _lt("URL Not Allowed")
	message = _lt("{url} is not on the site connected to this team.")


class UnsupportedCurrency(BuzzAPIError):
	title = _lt("Currency Not Supported")
	message = _lt("Buzz cannot take payments in {currency}.")


class RefundExceedsBalance(BuzzAPIError):
	title = _lt("Refund Too Large")
	message = _lt("Only {remaining} is left to refund on this order.")


class OrderNotFound(ResourceNotFound):
	message = _lt("This order does not exist.")


class RefundNotFound(ResourceNotFound):
	message = _lt("This refund does not exist.")
