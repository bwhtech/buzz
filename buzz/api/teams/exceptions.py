from frappe import _lt

from buzz.api.exceptions import NotPermitted


class NotATeamMember(NotPermitted):
	message = _lt("You are not a member of this team.")
