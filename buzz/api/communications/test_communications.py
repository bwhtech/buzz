from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from buzz.api.communications import (
	count_recipients,
	get_event_communications,
	send_communication,
	update_support_email,
)
from buzz.api.communications.exceptions import CannotSendCommunication, NoRecipients
from buzz.api.events.exceptions import CannotManageEvent
from buzz.api.teams.exceptions import CannotEditTeam
from buzz.tests.factories import (
	BuzzEventFactory,
	BuzzTeamFactory,
	BuzzTeamMembershipFactory,
	EventTicketFactory,
	TalkProposalFactory,
	UserFactory,
)
from buzz.tests.utils import html_part, queued_emails, queued_recipients


def forget_outgoing_account() -> None:
	if hasattr(frappe.local, "outgoing_email_account"):
		delattr(frappe.local, "outgoing_email_account")


class CommunicationsTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("comms-owner@example.com").name
		cls.viewer = UserFactory.create_once("comms-viewer@example.com").name
		cls.manager = UserFactory.create_once("comms-manager@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.viewer, team_role="Viewer")
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.manager, team_role="Manager")

	def setUp(self):
		# CI has no outgoing account. Muted, frappe queues against a dummy one and never sends;
		# the dummy is cached on frappe.local, so it is dropped before the next module runs.
		frappe.flags.mute_emails = True
		self.addCleanup(setattr, frappe.flags, "mute_emails", False)
		self.addCleanup(forget_outgoing_account)
		# CI never builds assets, and every email inlines email.bundle.css through this lookup.
		self.enterContext(patch("frappe.utils.get_assets_json", return_value={}))
		self.event = str(BuzzEventFactory.create(team=self.team).name)

	def issue_ticket(self, attendee_email: str) -> str:
		return EventTicketFactory.create("submitted", event=self.event, attendee_email=attendee_email).name

	def propose_talk(self, speaker_email: str) -> str:
		speakers = [{"first_name": "Speaker", "email": speaker_email}]
		return TalkProposalFactory.create(event=self.event, speakers=speakers).name

	def set_support_email(self, support_email: str | None):
		BuzzTeamFactory.set_settings(self.team, {"support_email": support_email})


class TestCountRecipients(CommunicationsTestCase):
	def test_counts_every_submitted_ticket_holder_once(self):
		self.issue_ticket("one@example.com")
		self.issue_ticket("two@example.com")
		self.issue_ticket("one@example.com")  # a second ticket, same address
		EventTicketFactory.create(
			event=self.event, attendee_email="draft@example.com"
		)  # still being paid for

		with self.set_user(self.owner):
			self.assertEqual(count_recipients(self.event, "Guests").count, 2)

	def test_narrows_guests_by_ticket_type(self):
		ticket = EventTicketFactory.create("submitted", event=self.event, attendee_email="tiered@example.com")
		self.issue_ticket("other@example.com")

		with self.set_user(self.owner):
			count = count_recipients(self.event, "Guests", ticket_types=str(ticket.ticket_type)).count

		self.assertEqual(count, 1)

	def test_counts_proposal_speakers_once(self):
		self.propose_talk("speaker@example.com")
		self.propose_talk("speaker@example.com")
		self.propose_talk("second@example.com")

		with self.set_user(self.owner):
			self.assertEqual(count_recipients(self.event, "Speakers").count, 2)

	def test_narrows_speakers_by_proposal_status(self):
		accepted = self.propose_talk("yes@example.com")
		self.propose_talk("pending@example.com")
		frappe.db.set_value("Talk Proposal", accepted, "status", "Accepted")

		with self.set_user(self.owner):
			self.assertEqual(count_recipients(self.event, "Speakers", statuses="Accepted").count, 1)

	def test_an_outsider_is_refused(self):
		outsider = UserFactory.create_once("comms-outsider@example.com").name

		with self.set_user(outsider), self.assertRaises(CannotManageEvent):
			count_recipients(self.event, "Guests")


class TestSendCommunication(CommunicationsTestCase):
	def test_queues_one_email_per_guest_with_the_team_reply_to(self):
		self.set_support_email("help@example.com")
		self.issue_ticket("a@example.com")
		self.issue_ticket("b@example.com")

		with self.set_user(self.manager):
			sent = send_communication(self.event, "Guests", "<p>Doors open at 9.</p>", subject="Doors")

		self.assertEqual(sent.recipient_count, 2)
		self.assertEqual(queued_recipients(sent.name), {"a@example.com", "b@example.com"})
		self.assertIn("Reply-To: help@example.com", queued_emails(sent.name)[0].message)

	def test_without_a_support_email_replies_go_to_the_sender(self):
		self.set_support_email(None)
		self.issue_ticket("c@example.com")

		with self.set_user(self.manager):
			sent = send_communication(self.event, "Guests", "<p>Hi</p>")

		self.assertIn(f"Reply-To: {self.manager}", queued_emails(sent.name)[0].message)

	def test_a_schedule_lands_on_the_queue_as_send_after(self):
		self.issue_ticket("later@example.com")
		later = add_to_date(now_datetime(), hours=2).replace(microsecond=0)

		with self.set_user(self.manager):
			sent = send_communication(self.event, "Guests", "<p>Soon.</p>", scheduled_at=later)

		self.assertEqual(sent.scheduled_at, later)
		self.assertEqual(queued_emails(sent.name)[0].send_after, later)

	def test_no_subject_falls_back_to_the_event_title(self):
		title = "Comms Launch Night"
		frappe.db.set_value("Buzz Event", self.event, "title", title)
		frappe.clear_document_cache("Buzz Event", self.event)
		self.issue_ticket("titled@example.com")

		with self.set_user(self.manager):
			sent = send_communication(self.event, "Guests", "<p>Hi</p>")

		self.assertEqual(sent.subject, "")
		self.assertIn(f"Subject: {title}", queued_emails(sent.name)[0].message)

	def test_nobody_to_send_to_is_refused(self):
		with self.set_user(self.manager), self.assertRaises(NoRecipients):
			send_communication(self.event, "Speakers", "<p>Hi</p>")

	def test_a_viewer_cannot_send(self):
		self.issue_ticket("v@example.com")

		with self.set_user(self.viewer), self.assertRaises(CannotSendCommunication):
			send_communication(self.event, "Guests", "<p>Hi</p>")


class TestGetEventCommunications(CommunicationsTestCase):
	def test_lists_what_was_sent_newest_first_with_the_sender(self):
		self.issue_ticket("list@example.com")
		with self.set_user(self.manager):
			first = send_communication(self.event, "Guests", "<p>One</p>", subject="First")
			second = send_communication(self.event, "Guests", "<p>Two</p>", subject="Second")

		with self.set_user(self.viewer):
			page = get_event_communications(self.event)

		self.assertEqual([row.name for row in page.communications], [second.name, first.name])
		self.assertEqual(page.communications[0].sent_by, frappe.utils.get_fullname(self.manager))
		self.assertFalse(page.can_write)
		self.assertFalse(page.can_edit_settings)

	def test_carries_the_filter_options_and_the_support_email(self):
		self.set_support_email("team@example.com")
		self.issue_ticket("opt@example.com")

		with self.set_user(self.owner):
			page = get_event_communications(self.event)

		self.assertEqual(page.support_email, "team@example.com")
		self.assertTrue(page.ticket_types)
		self.assertIn("Accepted", page.statuses)
		self.assertTrue(page.can_edit_settings)


class TestUpdateSupportEmail(CommunicationsTestCase):
	def test_an_owner_sets_the_team_support_email(self):
		with self.set_user(self.owner):
			update_support_email(self.event, "reply@example.com")

		self.assertEqual(
			frappe.db.get_value("Buzz Team Settings", self.team, "support_email"), "reply@example.com"
		)

	def test_a_manager_cannot(self):
		with self.set_user(self.manager), self.assertRaises(CannotEditTeam):
			update_support_email(self.event, "reply@example.com")

	def test_a_bad_address_is_refused(self):
		with self.set_user(self.owner), self.assertRaises(frappe.InvalidEmailAddressError):
			update_support_email(self.event, "not-an-email")


class TestCommunicationTemplate(CommunicationsTestCase):
	def test_wraps_the_message_in_the_event_header_and_footer(self):
		title, route = "Comms Template Night", f"comms-{frappe.generate_hash(length=6)}"
		html = self.sent_html(title=title, route=route)

		self.assertIn(title, html)
		self.assertIn("Bring a jacket.", html)
		self.assertIn("View event", html)
		self.assertIn(f"/events/{route}", html)
		self.assertIn("reply to this email", html)
		self.assertNotIn("Unsubscribe", html)

	def test_shows_the_banner_only_when_the_event_has_one(self):
		self.assertNotIn("data-banner", self.sent_html())

	def test_shows_the_banner_when_the_event_has_one(self):
		html = self.sent_html(banner_image="/files/banner.png")

		self.assertIn("/files/banner.png", html)

	def sent_html(self, **event_values) -> str:
		if event_values:
			frappe.db.set_value("Buzz Event", self.event, event_values)
			frappe.clear_document_cache("Buzz Event", self.event)
		self.issue_ticket("template@example.com")
		with self.set_user(self.manager):
			sent = send_communication(self.event, "Guests", "<p>Bring a jacket.</p>")
		return html_part(queued_emails(sent.name)[0].message)
