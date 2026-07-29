from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, Conflict, ResourceNotFound


class EventNotFound(ResourceNotFound):
	message = _lt("Event not found")


class FormNotAvailable(ResourceNotFound):
	message = _lt("This form is not available for this event")


class ProposalsNotAccepted(ResourceNotFound):
	message = _lt("Event Proposals are not being accepted")


class LoginRequired(BuzzAPIError):
	# BaseCustomEventForm.vue and EventProposalForm.vue branch on this exc_type.
	http_status_code = 401
	title = _lt("Login Required")
	message = _lt("Please log in to submit this form")


class SubmissionsClosed(Conflict):
	title = _lt("Submissions Closed")
	message = _lt("Submissions for this form have closed.")


class UnknownExcludedFields(BuzzAPIError):
	title = _lt("Unknown Fields")
	message = _lt("These fields do not exist on the {form_doctype} form: {fieldnames}")


class MandatoryFieldsHidden(BuzzAPIError):
	title = _lt("Mandatory Fields")
	message = _lt("These mandatory fields cannot be hidden on the {form_doctype} form: {fieldnames}")
