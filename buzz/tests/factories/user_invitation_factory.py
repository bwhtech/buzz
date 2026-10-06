from typing import Any

import frappe
from frappe.core.doctype.user_invitation.user_invitation import UserInvitation
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory


class UserInvitationFactory(BaseFactory[UserInvitation]):
	"""A pending buzz invitation that names no team. `insert` mails it, so patch `frappe.sendmail`."""

	doctype = "User Invitation"

	@property
	def default_attributes(self) -> dict[str, Any]:
		# Core allows one pending invitation per address per app, so every address is new.
		return {
			"email": f"invitee-{frappe.generate_hash(length=8)}@example.com",
			"roles": [{"role": "Buzz User"}],
			"app_name": "buzz",
			"redirect_to_path": "/b/manage",
		}
