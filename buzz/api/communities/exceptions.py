from frappe import _lt

from buzz.api.exceptions import Conflict, NotPermitted


class CannotSubmitEvent(NotPermitted):
	message = _lt("Only the event team's owners, admins and managers can send it to a community.")


class CannotReviewRequests(NotPermitted):
	message = _lt("Only the community's owners, admins and managers can review its events.")


class RequestNotPending(Conflict):
	message = _lt("This request has been reviewed already.")


class RequestNotRejected(Conflict):
	message = _lt("Only a rejected request can be submitted again.")


class RequestNotApproved(Conflict):
	message = _lt("Only an approved event can be removed from the community.")
