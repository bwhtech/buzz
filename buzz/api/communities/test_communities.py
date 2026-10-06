from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.communities import (
	add_event,
	approve_request,
	get_event_requests,
	get_requests,
	get_submittable_events,
	reject_request,
	remove_event,
	resubmit_request,
	submit_event,
	withdraw_request,
)
from buzz.api.communities.exceptions import (
	CannotReviewRequests,
	CannotSubmitEvent,
	RequestNotPending,
	RequestNotRejected,
)
from buzz.events.doctype.buzz_team.team_page import TeamPage
from buzz.events.doctype.buzz_team_membership.buzz_team_membership import upsert_membership
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, UserFactory

SENDMAIL = "buzz.api.communities.notifications.frappe.sendmail"


class CommunityTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.organiser = UserFactory.create_once("community-organiser@example.com").name
		cls.viewer = UserFactory.create_once("community-viewer@example.com").name
		cls.curator = UserFactory.create_once("community-curator@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.organiser, team_name="Chapter Builders").name
		upsert_membership(cls.team, cls.viewer, "Viewer")
		cls.community = BuzzTeamFactory.create_owned_by(
			cls.curator, "community", team_name="Builders United"
		).name
		cls.other_community = BuzzTeamFactory.create_owned_by(cls.curator, "community").name

	@classmethod
	def create_event(cls, title: str, **overrides):
		day = add_days(today(), 10)
		attributes = {"title": title, "team": cls.team, "start_date": day, "end_date": day}
		return str(BuzzEventFactory.create(**(attributes | overrides)).name)

	def setUp(self):
		# Rollback is per class, so each test gets an event no other test has submitted.
		self.event_title = f"Chapter Meetup {frappe.generate_hash(length=6)}"
		self.event = self.create_event(self.event_title)
		patcher = patch(SENDMAIL)
		self.sendmail = patcher.start()
		self.addCleanup(patcher.stop)

	def tearDown(self):
		frappe.set_user("Administrator")

	def submit(self, event=None, community=None) -> str:
		frappe.set_user(self.organiser)
		submit_event(event or self.event, community or self.community)
		frappe.set_user("Administrator")
		return frappe.db.get_value(
			"Community Event Request",
			{"event": event or self.event, "community": community or self.community},
		)

	def status_of(self, request: str) -> str:
		return frappe.db.get_value("Community Event Request", request, "status")


class TestSubmitting(CommunityTestCase):
	def test_a_submitted_request_waits_for_review(self):
		request = self.submit()

		self.assertEqual(self.status_of(request), "Pending")
		self.assertEqual(
			frappe.db.get_value("Community Event Request", request, "submitted_by"), self.organiser
		)

	def test_one_event_can_go_to_two_communities_but_once_each(self):
		self.submit()
		self.submit(community=self.other_community)

		with self.assertRaises(frappe.DuplicateEntryError):
			self.submit()

	def test_a_viewer_cannot_submit(self):
		frappe.set_user(self.viewer)

		with self.assertRaises(CannotSubmitEvent):
			submit_event(self.event, self.community)

	def test_a_team_that_is_not_a_community_is_refused(self):
		plain_team = BuzzTeamFactory.create_owned_by(self.curator, is_published=1).name

		with self.assertRaises(frappe.ValidationError):
			self.submit(community=plain_team)

	def test_an_unpublished_event_is_refused(self):
		draft = self.create_event("Draft Meetup", is_published=0)

		with self.assertRaises(frappe.ValidationError):
			self.submit(event=draft)

	def test_the_community_managers_are_emailed(self):
		self.submit()

		self.assertEqual(self.sendmail.call_args.kwargs["recipients"], [self.curator])

	def test_communities_already_asked_are_not_offered_again(self):
		self.submit()
		frappe.set_user(self.organiser)

		offered = [community.name for community in get_event_requests(self.event).communities]

		self.assertNotIn(self.community, offered)
		self.assertIn(self.other_community, offered)

	def test_the_page_offers_only_events_not_yet_submitted(self):
		other = self.create_event("Second Meetup")
		self.submit()
		frappe.set_user(self.organiser)

		offered = [event.name for event in get_submittable_events(self.community)]

		self.assertIn(other, offered)
		self.assertNotIn(self.event, offered)


class TestReviewing(CommunityTestCase):
	def review(self, method, *args):
		frappe.set_user(self.curator)
		method(*args)
		frappe.set_user("Administrator")

	def test_approving_lists_the_event_on_the_community_page(self):
		request = self.submit()

		self.review(approve_request, request)

		self.assertEqual(self.status_of(request), "Approved")
		self.assertIn(self.event_title, self.page_titles())
		self.assertEqual(self.sendmail.call_args.kwargs["recipients"], [self.organiser])

	def test_pending_and_rejected_events_stay_off_the_page(self):
		self.submit()
		rejected = self.submit(community=self.other_community)

		self.review(reject_request, rejected, "Not a fit")

		self.assertNotIn(self.event_title, self.page_titles())
		self.assertEqual(frappe.db.get_value("Community Event Request", rejected, "review_note"), "Not a fit")

	def test_an_event_team_manager_cannot_review(self):
		request = self.submit()
		frappe.set_user(self.organiser)

		with self.assertRaises(CannotReviewRequests):
			approve_request(request)

	def test_a_reviewed_request_cannot_be_reviewed_again(self):
		request = self.submit()
		self.review(approve_request, request)

		with self.assertRaises(RequestNotPending):
			self.review(reject_request, request)

	def test_a_rejected_request_can_be_resubmitted(self):
		request = self.submit()
		self.review(reject_request, request)
		frappe.set_user(self.organiser)

		resubmit_request(request)

		self.assertEqual(self.status_of(request), "Pending")

	def test_only_a_rejected_request_is_resubmitted(self):
		request = self.submit()
		frappe.set_user(self.organiser)

		with self.assertRaises(RequestNotRejected):
			resubmit_request(request)

	def test_removing_an_approved_event_rejects_it(self):
		request = self.submit()
		self.review(approve_request, request)

		self.review(remove_event, request)

		self.assertEqual(self.status_of(request), "Rejected")

	def test_deleting_a_submitted_event_takes_its_requests_along(self):
		request = self.submit()
		# The defaults made with every event block a delete on their own links.
		for doctype in ("Sponsorship Tier", "Event Ticket Type"):
			frappe.db.delete(doctype, {"event": self.event})

		frappe.delete_doc("Buzz Event", self.event)

		self.assertFalse(frappe.db.exists("Community Event Request", request))

	def test_withdrawing_deletes_the_request(self):
		request = self.submit()
		frappe.set_user(self.organiser)

		withdraw_request(request)

		self.assertFalse(frappe.db.exists("Community Event Request", request))

	def test_a_curator_adds_an_event_directly(self):
		self.review(add_event, self.community, self.event)
		frappe.set_user(self.curator)

		queue = get_requests(self.community)

		self.assertEqual([request.event for request in queue.approved], [self.event])
		self.assertEqual(queue.pending, [])

	def page_titles(self) -> list[str]:
		context = TeamPage(frappe.get_doc("Buzz Team", self.community)).as_context()
		return [event["title"] for day in context["upcoming_days"] for event in day["events"]]
