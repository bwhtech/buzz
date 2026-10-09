import frappe
from frappe import _
from frappe.utils import format_datetime, get_url

from buzz.events.doctype.buzz_team_settings.buzz_team_settings import get_team_settings
from buzz.permissions import WRITE_ROLES


def community_managers(community: str) -> list[str]:
	filters = {"team": community, "enabled": 1, "team_role": ["in", list(WRITE_ROLES)]}
	return frappe.get_all("Buzz Team Membership", filters=filters, pluck="user")


def community_contact(community: str) -> str | None:
	"""Where a submitter's reply goes: the community's support email, else its owner."""
	owner = {"team": community, "enabled": 1, "team_role": "Owner"}
	return get_team_settings(community).support_email or frappe.db.get_value(
		"Buzz Team Membership", owner, "user"
	)


def team_name(team: str) -> str:
	return frappe.db.get_value("Buzz Team", team, "team_name")


def submitting_team(request) -> str:
	# An external event has no Buzz team; its host stands in.
	return team_name(request.event_team) if request.event_team else request.host


def external_event(request) -> dict | None:
	"""What the email shows for an event hosted elsewhere; a Buzz event gets the base header."""
	if not request.is_external_event:
		return None
	return frappe._dict(
		title=request.event_title,
		when=format_datetime(request.start_datetime, "EEE, d MMM yyyy, h:mm a"),
		place=request.event_location,
		host=request.host,
		url=request.event_url,
	)


def send_email(
	request, recipients: list[str], subject: str, template: str, reply_to: str | None = None, **args
) -> None:
	frappe.sendmail(
		recipients=recipients,
		reply_to=reply_to,
		subject=subject,
		template=template,
		raw_html=True,
		add_css=False,
		args={
			"event_title": request.event_title,
			"community_name": team_name(request.community),
			"event_doc": frappe.get_cached_doc("Buzz Event", request.event) if request.event else None,
			"external_event": external_event(request),
			**args,
		},
		reference_doctype=request.doctype,
		reference_name=request.name,
	)


def notify_submitted(request) -> None:
	"""Tells the submitter it arrived, and the community's managers it needs a review."""
	if request.submitted_by:
		send_email(
			request,
			[request.submitted_by],
			_("{0} was sent to {1}").format(request.event_title, team_name(request.community)),
			"community_event_received",
			reply_to=community_contact(request.community),
		)
	send_email(
		request,
		community_managers(request.community),
		_("{0} submitted {1}").format(submitting_team(request), request.event_title),
		"community_event_submitted",
		reply_to=request.submitted_by,
		team_name=submitting_team(request),
		review_url=get_url(f"/b/manage/communities/{request.community}/calendar"),
	)


def notify_reviewed(request) -> None:
	# A request made in Desk names no submitter, so there is nobody to tell.
	if not request.submitted_by:
		return
	approved = request.status == "Approved"
	community_route = frappe.db.get_value("Buzz Team", request.community, "route")
	send_email(
		request,
		[request.submitted_by],
		(_("{0} was approved") if approved else _("{0} was not approved")).format(request.event_title),
		"community_event_approved" if approved else "community_event_rejected",
		reply_to=community_contact(request.community),
		community_url=get_url(f"/{community_route}"),
		review_note=request.review_note,
	)
