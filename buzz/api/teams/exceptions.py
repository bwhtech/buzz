from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, Conflict, NotPermitted


class NotATeamMember(NotPermitted):
	message = _lt("You are not a member of this team.")


class CannotManageMembers(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You cannot manage members of this team.")


class CannotEditTeam(NotPermitted):
	message = _lt("You cannot edit this team.")


class CannotGrantOwnership(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("Ownership of a team cannot be granted.")


class UnknownTeamRole(BuzzAPIError):
	title = _lt("Invalid Role")
	message = _lt("{team_role} is not a team role.")


class NoPendingInvite(BuzzAPIError):
	title = _lt("No Invitation")
	message = _lt("There is no pending invitation for {email}.")


class InvalidTeamSlug(BuzzAPIError):
	title = _lt("Invalid URL")
	message = _lt("Use letters, numbers and hyphens for the team's URL.")


class TeamSlugTaken(Conflict):
	title = _lt("URL Taken")
	message = _lt("Another team already uses {slug}.")
