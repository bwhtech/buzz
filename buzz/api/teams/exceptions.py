from frappe import _lt

from buzz.api.exceptions import NotPermitted


class NotATeamMember(NotPermitted):
	title = _lt("Not Permitted")
	message = _lt("You are not a member of this team.")
