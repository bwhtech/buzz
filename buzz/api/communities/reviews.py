import frappe

from buzz.api.communities.exceptions import CannotReviewRequests, RequestNotApproved, RequestNotPending
from buzz.api.communities.notifications import notify_reviewed
from buzz.api.communities.queries import not_in_filter, request_rows, upcoming_event_options
from buzz.api.communities.schemas import CommunityQueue, EventOption
from buzz.permissions import has_team_access

REQUEST = "Community Event Request"


class CommunityReview:
	"""A community's queue: approve, reject or remove events from other teams, or add them."""

	def __init__(self, community: str):
		if not community or not has_team_access(community, "write", frappe.session.user):
			CannotReviewRequests.throw()
		self.community = community

	@classmethod
	def from_request(cls, request: str) -> tuple["CommunityReview", "frappe.model.document.Document"]:
		doc = frappe.get_doc(REQUEST, request)
		return cls(doc.community), doc

	def queue(self) -> CommunityQueue:
		return CommunityQueue(
			pending=request_rows(community=self.community, status="Pending"),
			approved=request_rows(community=self.community, status="Approved"),
		)

	def review(self, request, status: str, note: str | None = None) -> None:
		if request.status != "Pending":
			RequestNotPending.throw()
		self.set_status(request, status, note)
		notify_reviewed(request)

	def remove(self, request) -> None:
		if request.status != "Approved":
			RequestNotApproved.throw()
		self.set_status(request, "Rejected")

	def add(self, event: str) -> None:
		"""Lists an event straight away, reusing the event's earlier request if it has one."""
		name = frappe.db.get_value(REQUEST, {"event": event, "community": self.community})
		request = frappe.get_doc(REQUEST, name) if name else frappe.new_doc(REQUEST)
		request.update({"event": event, "community": self.community})
		request.submitted_by = request.submitted_by or frappe.session.user
		self.set_status(request, "Approved")

	def set_status(self, request, status: str, note: str | None = None) -> None:
		request.update({"status": status, "reviewed_by": frappe.session.user, "review_note": note})
		request.save(ignore_permissions=True)

	def addable_events(self, txt: str) -> list[EventOption]:
		listed = frappe.get_all(
			REQUEST, filters={"community": self.community, "status": "Approved"}, pluck="event"
		)
		filters = {
			"team": ["!=", self.community],
			"name": not_in_filter(listed),
			"title": ["like", f"%{txt}%"],
		}
		return upcoming_event_options(filters)
