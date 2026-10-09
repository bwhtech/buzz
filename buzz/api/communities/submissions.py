import frappe
from frappe.rate_limiter import rate_limit

from buzz.api.communities.exceptions import CannotSubmitEvent, RequestNotRejected
from buzz.api.communities.notifications import notify_submitted
from buzz.api.communities.queries import request_rows, upcoming_event_options
from buzz.api.communities.schemas import CommunityOption, EventOption, EventRequests, ExternalEvent
from buzz.permissions import WRITE_ROLES, has_team_access

REQUEST = "Community Event Request"


class EventSubmissions:
	"""One event's requests to communities, made by the event's own team."""

	def __init__(self, event: str):
		self.event = str(event)
		self.team = frappe.db.get_value("Buzz Event", self.event, "team")
		if not self.team or not has_team_access(self.team, "write", frappe.session.user):
			CannotSubmitEvent.throw()

	@classmethod
	def from_request(cls, request: str) -> tuple["EventSubmissions", "frappe.model.document.Document"]:
		doc = frappe.get_doc(REQUEST, request)
		return cls(doc.event), doc

	def overview(self) -> EventRequests:
		return EventRequests(requests=request_rows(event=self.event), communities=self.open_communities())

	def open_communities(self) -> list[CommunityOption]:
		asked = frappe.get_all(REQUEST, filters={"event": self.event}, pluck="community")
		filters = {
			"accept_community_submissions": 1,
			"is_published": 1,
			"name": ["not in", [*asked, self.team]],
		}
		rows = frappe.get_all(
			"Buzz Team", filters=filters, fields=["name", "team_name", "logo"], order_by="team_name"
		)
		return [CommunityOption(**row) for row in rows]

	def submit(self, community: str) -> None:
		request = frappe.get_doc(
			{
				"doctype": REQUEST,
				"event": self.event,
				"community": community,
				"submitted_by": frappe.session.user,
			}
		)
		request.insert(ignore_permissions=True)
		notify_submitted(request)

	def resubmit(self, request) -> None:
		if request.status != "Rejected":
			RequestNotRejected.throw()
		request.update(
			{
				"status": "Pending",
				"submitted_by": frappe.session.user,
				"reviewed_by": None,
				"review_note": None,
			}
		)
		request.save(ignore_permissions=True)
		notify_submitted(request)

	def withdraw(self, request) -> None:
		request.delete(ignore_permissions=True)


def submittable_events(community: str) -> list[EventOption]:
	"""The session user's upcoming events this community has not been asked about."""
	membership = {
		"user": frappe.session.user,
		"enabled": 1,
		"team_role": ["in", list(WRITE_ROLES)],
		"team": ["!=", community],
	}
	teams = frappe.get_all("Buzz Team Membership", filters=membership, pluck="team")
	if not teams:
		return []
	asked = frappe.get_all(REQUEST, filters={"community": community}, pluck="event")
	return upcoming_event_options({"team": ["in", teams], "name": ["not in", asked]})


def external_request(community: str, event: ExternalEvent):
	"""An unsaved request for an event hosted on another platform."""
	request = frappe.new_doc(REQUEST)
	request.update(event.model_dump())
	request.update({"is_external_event": 1, "community": community, "submitted_by": frappe.session.user})
	return request


# Here, not on the endpoint: stacked under whitelist it hides the ExternalEvent annotation.
# Open to anyone signed in, and each call emails the community's managers.
@rate_limit(limit=10, seconds=60 * 60)
def submit_external_request(community: str, event: ExternalEvent) -> None:
	"""Anyone signed in may suggest an external event; the community reviews it."""
	request = external_request(community, event)
	request.insert(ignore_permissions=True)
	notify_submitted(request)
