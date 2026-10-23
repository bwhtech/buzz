import frappe
from frappe.core.doctype.communication.email import make as make_communication
from frappe.desk.form.utils import add_comment
from frappe.utils import get_fullname, sanitize_html, validate_email_address

from buzz.api.comments.activity import ActivityFeed
from buzz.api.comments.exceptions import CannotDeleteComment, NoRecipients, NotCommentable, NotTeamMember
from buzz.api.comments.schemas import ActivityEntry
from buzz.api.teams.schemas import TeamMember
from buzz.api.teams.services import members_of
from buzz.comments import is_commentable, note_email_args, team_of
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


def render_email(template: str, args: dict) -> str:
	# nosemgrep: frappe-ssti
	return frappe.render_template(f"buzz/templates/emails/{template}.html", args, is_path=True)


def send_in_layout(communication: str, html: str) -> None:
	"""Sends a stored Communication with `html` as its body, keeping its message-id so
	replies thread onto it."""
	message = frappe.get_doc("Communication", communication).sendmail_input_dict(raw_html=True, add_css=False)
	if not message:
		frappe.throw(frappe._("No outgoing email account is set up."), exc=frappe.OutgoingEmailError)
	frappe.sendmail(**{**message, "content": html})


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

	def activity(self) -> list[ActivityEntry]:
		return ActivityFeed(self.reference_doctype, self.reference_name).entries()

	def members(self) -> list[TeamMember]:
		return members_of(self.team)

	def add(
		self,
		content: str,
		email_recipients: bool = False,
		cc: list[str] | None = None,
		bcc: list[str] | None = None,
	) -> str:
		"""A team note is a Comment; one emailed to the record's outside party is a Communication."""
		if email_recipients:
			return self.email(content, cc or [], bcc or [])
		user = frappe.session.user
		return add_comment(
			self.reference_doctype, self.reference_name, content, user, get_fullname(user)
		).name

	def delete(self, name: str) -> None:
		if not self.can_delete(frappe.db.get_value("Comment", name, "owner")):
			CannotDeleteComment.throw()
		frappe.delete_doc("Comment", name, ignore_permissions=True)

	def can_delete(self, owner: str) -> bool:
		user = frappe.session.user
		return owner == user or is_unrestricted(user) or team_role_of(user, self.team) in ADMIN_ROLES

	def email_sender(self) -> str | None:
		return frappe.db.get_value("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "email_id")

	def email(self, content: str, cc: list[str], bcc: list[str]) -> str:
		recipient_source = EMAIL_RECIPIENTS.get(self.reference_doctype)
		recipients = recipient_source(self.reference_name) if recipient_source else []
		if not recipients:
			NoRecipients.throw()
		for address in [*cc, *bcc]:
			validate_email_address(address, throw=True)
		# Comment.validate cleans a note; Communication stores what it is given.
		note = sanitize_html(content, always_sanitize=True)
		args = note_email_args(self.reference_doctype, self.reference_name, frappe.session.user, note)
		# Stored as the plain note for the activity feed; sent in the Buzz email layout.
		communication = make_communication(
			doctype=self.reference_doctype,
			name=self.reference_name,
			subject=frappe._("A note on {0}").format(args["record_title"]),
			content=note,
			recipients=recipients,
			cc=cc,
			bcc=bcc,
			send_email=False,
		)["name"]
		send_in_layout(communication, render_email("proposal_note", args))
		return communication
