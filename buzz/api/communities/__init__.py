import frappe

from buzz.api.communities.reviews import CommunityReview
from buzz.api.communities.schemas import CommunityQueue, EventOption, EventRequests
from buzz.api.communities.submissions import EventSubmissions, submittable_events


@frappe.whitelist()
def get_event_requests(event: str) -> EventRequests:
	return EventSubmissions(event).overview()


@frappe.whitelist()
def get_submittable_events(community: str) -> list[EventOption]:
	return submittable_events(community)


@frappe.whitelist(methods=["POST"])
def submit_event(event: str, community: str) -> None:
	EventSubmissions(event).submit(community)


@frappe.whitelist(methods=["POST"])
def resubmit_request(request: str) -> None:
	submissions, doc = EventSubmissions.from_request(request)
	submissions.resubmit(doc)


@frappe.whitelist(methods=["POST"])
def withdraw_request(request: str) -> None:
	submissions, doc = EventSubmissions.from_request(request)
	submissions.withdraw(doc)


@frappe.whitelist()
def get_requests(community: str) -> CommunityQueue:
	return CommunityReview(community).queue()


@frappe.whitelist(methods=["POST"])
def approve_request(request: str) -> None:
	community_review, doc = CommunityReview.from_request(request)
	community_review.review(doc, "Approved")


@frappe.whitelist(methods=["POST"])
def reject_request(request: str, note: str | None = None) -> None:
	community_review, doc = CommunityReview.from_request(request)
	community_review.review(doc, "Rejected", note)


@frappe.whitelist(methods=["POST"])
def remove_event(request: str) -> None:
	community_review, doc = CommunityReview.from_request(request)
	community_review.remove(doc)


@frappe.whitelist(methods=["POST"])
def add_event(community: str, event: str) -> None:
	CommunityReview(community).add(event)
