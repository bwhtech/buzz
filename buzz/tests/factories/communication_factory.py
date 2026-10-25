from typing import Any

from frappe.core.doctype.communication.communication import Communication
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory


class CommunicationFactory(BaseFactory[Communication]):
	"""An email received on a new talk proposal unless told otherwise."""

	doctype = "Communication"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import TalkProposalFactory

		return {
			"communication_type": "Communication",
			"communication_medium": "Email",
			"sent_or_received": "Received",
			"subject": "Re: your proposal",
			"content": "<p>Reply</p>",
			"sender": "speaker@example.com",
			"reference_doctype": "Talk Proposal",
			"reference_name": self.overrides.get("reference_name") or TalkProposalFactory.create().name,
		}
