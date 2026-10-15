from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, NotPermitted


class NotCommentable(BuzzAPIError):
	title = _lt("Cannot Comment")
	message = _lt("These records do not take comments.")


class NotTeamMember(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("Only members of this team can see its comments.")


class CannotDeleteComment(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("Only the author or a team admin can delete this comment.")


class NoRecipients(BuzzAPIError):
	title = _lt("No Recipients")
	message = _lt("There is no one to email on this record.")
