from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.communities import (
	add_event,
	add_external_event,
	approve_request,
	find_event,
	get_event_requests,
	get_requests,
	get_submittable_events,
	reject_request,
	remove_event,
	resubmit_request,
	submit_event,
	submit_external_event,
	withdraw_request,
)
from buzz.api.communities.exceptions import (
	CannotReviewRequests,
	CannotSubmitEvent,
	EventNotFound,
	RequestNotPending,
	RequestNotRejected,
)
from buzz.api.teams import get_team_events
from buzz.events.doctype.buzz_team.team_page import TeamPage
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory

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
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.viewer, team_role="Viewer")
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

	def emails(self) -> list[tuple[list[str], str]]:
		return [(call.kwargs["recipients"], call.kwargs["template"]) for call in self.sendmail.call_args_list]

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

	def test_the_submitter_and_the_community_managers_are_emailed(self):
		self.submit()

		self.assertEqual(
			self.emails(),
			[([self.organiser], "community_event_received"), ([self.curator], "community_event_submitted")],
		)

	def test_replies_reach_the_other_side(self):
		self.submit()

		received, submitted = (call.kwargs["reply_to"] for call in self.sendmail.call_args_list)
		self.assertEqual((received, submitted), (self.curator, self.organiser))

	def test_administrator_is_never_emailed(self):
		BuzzTeamMembershipFactory.create(team=self.community, user="Administrator", team_role="Manager")

		self.submit()

		self.assertNotIn("Administrator", self.sendmail.call_args.kwargs["recipients"])

	def set_support_email(self, email: str | None) -> None:
		frappe.db.set_value("Buzz Team Settings", self.community, "support_email", email)
		frappe.clear_document_cache("Buzz Team Settings", self.community)

	def test_a_community_support_email_takes_replies_over_its_owner(self):
		self.set_support_email("hello@builders.example.com")
		# Rollback is per class, so the next test must see the community without it.
		self.addCleanup(self.set_support_email, None)

		self.submit()

		self.assertEqual(self.sendmail.call_args_list[0].kwargs["reply_to"], "hello@builders.example.com")

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

	def test_pending_requests_list_the_newest_submission_first(self):
		# The older submission starts sooner, so start-date order would list it first.
		sooner = add_days(today(), 5)
		older = self.submit(self.create_event("Older", start_date=sooner, end_date=sooner))
		newer = self.submit()
		frappe.db.set_value("Community Event Request", older, "creation", "2026-01-01 09:00:00")
		frappe.set_user(self.curator)

		pending = [row.name for row in get_requests(self.community).pending]

		self.assertLess(pending.index(newer), pending.index(older))

	def test_a_curator_finds_an_event_by_its_link(self):
		route = frappe.db.get_value("Buzz Event", self.event, "route")
		frappe.set_user(self.curator)

		found = find_event(f"https://buzz.example.com/events/{route}/")

		self.assertEqual((found.name, found.title), (self.event, self.event_title))
		with self.assertRaises(EventNotFound):
			find_event("https://buzz.example.com/events/no-such-event")

	def test_anyone_signed_in_submits_an_external_event_for_review(self):
		frappe.set_user(self.viewer)

		submit_external_event(self.community, self.external_event())

		frappe.set_user(self.curator)
		pending = [row for row in get_requests(self.community).pending if row.is_external_event]
		self.assertEqual([row.event_title for row in pending], ["Rust Meetup"])
		self.assertEqual(
			self.emails(),
			[([self.viewer], "community_event_received"), ([self.curator], "community_event_submitted")],
		)

	def test_an_external_event_link_must_be_http(self):
		frappe.set_user(self.viewer)

		with self.assertRaises(frappe.ValidationError):
			submit_external_event(
				self.community, self.external_event() | {"event_url": "javascript:alert(1)"}
			)

	def test_an_external_event_keeps_a_long_tracking_link_but_not_a_long_name(self):
		frappe.set_user(self.viewer)
		link = "https://lu.ma/rust?" + "utm_source=newsletter&utm_campaign=october-community-roundup&" * 4

		# Rollback is per class, so this goes to the other community and stays out of its tests.
		submit_external_event(self.other_community, self.external_event() | {"event_url": link})

		self.assertTrue(frappe.db.exists("Community Event Request", {"event_url": link}))
		with self.assertRaises(frappe.FrappeTypeError):
			submit_external_event(self.other_community, self.external_event() | {"event_title": "Rust " * 30})

	def test_a_curator_adds_an_external_event(self):
		event = {
			"event_title": "Rust Meetup",
			"host": "Rustaceans",
			"event_location": "WeWork, Bengaluru",
			"start_datetime": "2026-12-01 18:00:00",
			"end_datetime": "2026-12-01 20:00:00",
			"event_url": "https://lu.ma/rust",
		}
		self.review(add_external_event, self.community, event)
		frappe.set_user(self.curator)

		approved = get_requests(self.community).approved

		external = [request for request in approved if request.is_external_event]
		self.assertEqual(
			[(row.event_title, row.event_team_name) for row in external], [("Rust Meetup", "Rustaceans")]
		)

	def test_the_calendar_has_own_featured_and_external_events(self):
		own = self.create_event("Curators Meetup", team=self.community)
		self.review(add_event, self.community, self.event)
		self.review(add_external_event, self.community, self.external_event())
		frappe.set_user(self.viewer)

		upcoming = get_team_events(self.community).upcoming

		flags = {row.title: (row.is_community_request, row.is_external) for row in upcoming}
		self.assertEqual(flags["Curators Meetup"], (False, False))
		self.assertEqual(flags[self.event_title], (True, False))
		self.assertEqual(flags["Rust Meetup"], (True, True))
		self.assertIn(own, [row.name for row in upcoming])

	def test_only_curators_are_organizers_on_the_community_page(self):
		page = TeamPage(frappe.get_doc("Buzz Team", self.community))
		frappe.set_user(self.curator)
		self.assertTrue(page.is_organizer())
		frappe.set_user(self.organiser)
		self.assertFalse(page.is_organizer())
		frappe.set_user("Administrator")
		self.assertFalse(page.is_organizer())

	def external_event(self) -> dict:
		day = add_days(today(), 20)
		return {
			"event_title": "Rust Meetup",
			"host": "Rustaceans",
			"event_location": "WeWork, Bengaluru",
			"start_datetime": f"{day} 18:00:00",
			"end_datetime": f"{day} 20:00:00",
			"event_url": "https://lu.ma/rust",
		}

	def page_titles(self) -> list[str]:
		context = TeamPage(frappe.get_doc("Buzz Team", self.community)).as_context()
		return [event["title"] for day in context["upcoming_days"] for event in day["events"]]
