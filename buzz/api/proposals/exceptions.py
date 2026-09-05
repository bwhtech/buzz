from frappe import _lt

from buzz.api.exceptions import ResourceNotFound


class ProposalFormMissing(ResourceNotFound):
	title = _lt("No Proposal Form")
	message = _lt("This event has no talk proposal form to open or close.")
