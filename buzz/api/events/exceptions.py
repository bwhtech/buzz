from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, Conflict, NotPermitted, ResourceNotFound


class EventNotFound(ResourceNotFound):
	title = _lt("Event Not Found")
	message = _lt("This event does not exist.")


class CannotManageEvent(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You cannot manage this event.")


class CannotCreateEvents(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You cannot create events for this team.")


class ZoomNotAvailable(BuzzAPIError):
	title = _lt("Zoom Not Available")
	message = _lt("Zoom is not set up on this site, so a Zoom meeting cannot be created.")


class EventEnded(BuzzAPIError):
	title = _lt("Event Has Ended")
	message = _lt("You cannot convert events that have ended to Zoom meetings.")


class TaxDetailsMissing(BuzzAPIError):
	title = _lt("Tax Details Missing")
	message = _lt("Add your team's tax details before charging tax on tickets.")


class AlreadyOnTeam(Conflict):
	title = _lt("Already On The Team")
	message = _lt("{email} is on this event's team already, so they can already open the event.")


class AlreadyCollaborator(Conflict):
	title = _lt("Already A Collaborator")
	message = _lt("{email} already collaborates on this event.")


class UnknownCollaborator(ResourceNotFound):
	title = _lt("Collaborator Not Found")
	message = _lt("{email} has not been invited to this event.")


class InvalidCollaboratorInvitation(BuzzAPIError):
	title = _lt("Invitation Not Valid")
	message = _lt("This invitation link is invalid or has expired.")


class CollaboratorLoginRequired(NotPermitted):
	title = _lt("Log In To Continue")
	message = _lt("Log in as {email}, then open this invitation link again.")


class CollaboratorWrongAccount(NotPermitted):
	title = _lt("Wrong Account")
	message = _lt("This invitation was sent to another email address. Log out and open the link again.")


class InvalidSectionAccess(BuzzAPIError):
	title = _lt("Invalid Access Level")
	message = _lt("Access to {section} must be View or Edit, or left blank for none.")
