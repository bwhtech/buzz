import frappe
from frappe.core.doctype.communication.email import make as make_communication
from frappe.desk.form.load import get_comments
from frappe.desk.form.utils import add_comment
from frappe.utils import get_fullname

from buzz.api.comments.exceptions import CannotDeleteComment, NoRecipients, NotCommentable, NotTeamMember
from buzz.api.comments.schemas import CommentItem
from buzz.api.teams.schemas import TeamMember
from buzz.api.teams.services import members_of
from buzz.comments import is_commentable, team_of
from buzz.permissions import ADMIN_ROLES, has_team_access, is_unrestricted, team_role_of


def proposal_speaker_emails(proposal: str) -> list[str]:
	return frappe.get_all(
		"Proposal Speaker",
		filters={"parenttype": "Talk Proposal", "parent": proposal, "email": ("is", "set")},
		pluck="email",
		distinct=True,
	)


# Who a note can be emailed to, for records that have someone outside the team.
EMAIL_RECIPIENTS = {"Talk Proposal": proposal_speaker_emails}


class DocumentComments:
	"""Team notes on one record. Gated on team membership: a speaker reads their own proposal
	through its permission hook, so `frappe.has_permission` would let them in."""

	def __init__(self, reference_doctype: str, reference_name: str):
		if not is_commentable(reference_doctype):
			NotCommentable.throw()
		self.reference_doctype = reference_doctype
		self.reference_name = reference_name
		self.team = team_of(reference_doctype, reference_name)
		if not self.team or not has_team_access(self.team, "read", frappe.session.user):
			NotTeamMember.throw()

	@classmethod
	def of_comment(cls, name: str) -> "DocumentComments":
		reference = frappe.db.get_value(
			"Comment",
			{"name": name, "comment_type": "Comment"},
			["reference_doctype", "reference_name"],
			as_dict=True,
		)
		if not reference:
			frappe.throw(frappe._("Comment not found"), frappe.DoesNotExistError)
		return cls(reference.reference_doctype, reference.reference_name)

	def list(self) -> list[CommentItem]:
		comments = get_comments(self.reference_doctype, self.reference_name)[::-1]
		users = self.user_details({comment.owner for comment in comments})
		return [self.comment_item(comment, users.get(comment.owner)) for comment in comments]

	def members(self) -> list[TeamMember]:
		return members_of(self.team)

	def add(self, content: str, email_recipients: bool = False) -> str:
		user = frappe.session.user
		comment = add_comment(self.reference_doctype, self.reference_name, content, user, get_fullname(user))
		if email_recipients:
			self.email(comment.content)
		return comment.name

	def delete(self, name: str) -> None:
		if not self.can_delete(frappe.db.get_value("Comment", name, "owner")):
			CannotDeleteComment.throw()
		frappe.delete_doc("Comment", name, ignore_permissions=True)

	def can_delete(self, owner: str) -> bool:
		user = frappe.session.user
		return owner == user or is_unrestricted(user) or team_role_of(user, self.team) in ADMIN_ROLES

	def email(self, content: str) -> None:
		recipient_source = EMAIL_RECIPIENTS.get(self.reference_doctype)
		recipients = recipient_source(self.reference_name) if recipient_source else []
		if not recipients:
			NoRecipients.throw()
		title = frappe.db.get_value(self.reference_doctype, self.reference_name, "title")
		make_communication(
			doctype=self.reference_doctype,
			name=self.reference_name,
			subject=frappe._("Notes on {0}").format(title),
			content=content,
			recipients=recipients,
			send_email=True,
		)

	@staticmethod
	def user_details(users: set[str]) -> dict:
		rows = frappe.get_all(
			"User", filters={"name": ("in", list(users))}, fields=["name", "full_name", "user_image"]
		)
		return {row.name: row for row in rows}

	@staticmethod
	def comment_item(comment, user) -> CommentItem:
		return CommentItem(
			name=comment.name,
			content=comment.content,
			owner=comment.owner,
			owner_name=(user and user.full_name) or comment.owner,
			owner_image=user and user.user_image,
			creation=comment.creation,
		)
