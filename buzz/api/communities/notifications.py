import frappe
from frappe import _
from frappe.utils import get_url

from buzz.permissions import WRITE_ROLES


def community_managers(community: str) -> list[str]:
	filters = {"team": community, "enabled": 1, "team_role": ["in", list(WRITE_ROLES)]}
	return frappe.get_all("Buzz Team Membership", filters=filters, pluck="user")


def team_name(team: str) -> str:
	return frappe.db.get_value("Buzz Team", team, "team_name")


def send_email(request, recipients: list[str], subject: str, template: str, **args) -> None:
	frappe.sendmail(
		recipients=recipients,
		subject=subject,
		template=template,
		raw_html=True,
		add_css=False,
		args={"event_title": request.event_title, "community_name": team_name(request.community), **args},
		reference_doctype=request.doctype,
		reference_name=request.name,
	)


def notify_submitted(request) -> None:
	submitting_team = team_name(request.event_team)
	send_email(
		request,
		community_managers(request.community),
		_("{0} submitted {1}").format(submitting_team, request.event_title),
		"community_event_submitted",
		team_name=submitting_team,
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
		community_url=get_url(f"/{community_route}"),
		review_note=request.review_note,
	)
