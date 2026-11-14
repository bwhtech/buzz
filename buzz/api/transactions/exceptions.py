from frappe import _lt

from buzz.api.exceptions import ResourceNotFound


class TransactionNotFound(ResourceNotFound):
	title = _lt("Transaction Not Found")
	message = _lt("This transaction does not exist.")
