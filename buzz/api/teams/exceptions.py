from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, NotPermitted


class NotATeamMember(NotPermitted):
	message = _lt("You are not a member of this team.")


class CannotManageMembers(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You cannot manage members of this team.")


class CannotGrantOwnership(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("Ownership of a team cannot be granted.")


class UnknownTeamRole(BuzzAPIError):
	title = _lt("Invalid Role")
	message = _lt("{team_role} is not a team role.")
