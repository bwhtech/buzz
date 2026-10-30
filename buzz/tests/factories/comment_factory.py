from typing import Any

from frappe.core.doctype.comment.comment import Comment
from frappe_factory_bot.frappe_factory_bot.base_factory import BaseFactory


class CommentFactory(BaseFactory[Comment]):
	"""A team note on a new talk proposal unless told otherwise."""

	doctype = "Comment"

	@property
	def default_attributes(self) -> dict[str, Any]:
		from buzz.tests.factories import TalkProposalFactory

		return {
			"comment_type": "Comment",
			"reference_doctype": "Talk Proposal",
			"reference_name": self.overrides.get("reference_name") or TalkProposalFactory.create().name,
			"content": "<p>Note</p>",
		}
