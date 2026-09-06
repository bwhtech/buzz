from email import message_from_string

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
from buzz.api.events.test_events import create_event, issue_ticket
from buzz.api.teams.exceptions import CannotEditTeam
from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team, create_user
from buzz.proposals.doctype.talk_proposal.test_talk_proposal import make_guest_proposal
from buzz.test_permissions import add_member, create_ticket


def queued_emails(communication: str) -> list:
	return frappe.get_all(
		"Email Queue",
		filters={"reference_doctype": "Event Communication", "reference_name": communication},
		fields=["name", "send_after", "message"],
	)


def queued_recipients(communication: str) -> set[str]:
	queue_names = [row.name for row in queued_emails(communication)]
	if not queue_names:
		return set()
	return set(
		frappe.get_all("Email Queue Recipient", filters={"parent": ["in", queue_names]}, pluck="recipient")
	)


def html_part(raw_message: str) -> str:
	"""The HTML body, decoded: the queue stores it quoted-printable, wrapped at 76 columns."""
	for part in message_from_string(raw_message).walk():
		if part.get_content_type() == "text/html":
			return part.get_payload(decode=True).decode()
	return ""


class CommunicationsTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		for doctype, name in (("Event Category", "Test Category"), ("Event Host", "Test Host")):
			if not frappe.db.exists(doctype, name):
				frappe.get_doc({"doctype": doctype, "name": name}).insert(ignore_permissions=True)
		cls.owner = create_user("comms-owner@example.com", "Owner")
		cls.viewer = create_user("comms-viewer@example.com", "Viewer")
		cls.manager = create_user("comms-manager@example.com", "Manager")
		cls.team = create_owned_team("Comms Team", cls.owner)
		add_member(cls.team, cls.viewer, "Viewer")
		add_member(cls.team, cls.manager, "Manager")

	def setUp(self):
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		# CI has no outgoing account. Muted, frappe queues against a dummy one and never sends.
		frappe.flags.mute_emails = True
		self.addCleanup(setattr, frappe.flags, "mute_emails", False)
		self.event = create_event(f"Comms {frappe.generate_hash(length=6)}", self.team)


class TestCountRecipients(CommunicationsTestCase):
	def test_counts_every_submitted_ticket_holder_once(self):
		issue_ticket(self.event, "one@example.com")
		issue_ticket(self.event, "two@example.com")
		create_ticket(self.event, "one@example.com")  # a second ticket, same address
		create_ticket(self.event, "draft@example.com")  # unsubmitted: still being paid for
		frappe.set_user(self.owner)

		self.assertEqual(count_recipients(self.event, "Guests").count, 2)

	def test_narrows_guests_by_ticket_type(self):
		ticket = issue_ticket(self.event, "tiered@example.com")
		issue_ticket(self.event, "other@example.com")
		ticket_type = frappe.db.get_value("Event Ticket", ticket, "ticket_type")
		frappe.set_user(self.owner)

		self.assertEqual(count_recipients(self.event, "Guests", ticket_types=str(ticket_type)).count, 1)

	def test_counts_proposal_speakers_once(self):
		make_guest_proposal(self.event, "speaker@example.com")
		make_guest_proposal(self.event, "speaker@example.com")
		make_guest_proposal(self.event, "second@example.com")
		frappe.set_user(self.owner)

		self.assertEqual(count_recipients(self.event, "Speakers").count, 2)

	def test_narrows_speakers_by_proposal_status(self):
		accepted = make_guest_proposal(self.event, "yes@example.com")
		make_guest_proposal(self.event, "pending@example.com")
		frappe.db.set_value("Talk Proposal", accepted, "status", "Accepted")
		frappe.set_user(self.owner)

		self.assertEqual(count_recipients(self.event, "Speakers", statuses="Accepted").count, 1)

	def test_an_outsider_is_refused(self):
		frappe.set_user(create_user("comms-outsider@example.com", "Outsider"))

		with self.assertRaises(CannotManageEvent):
			count_recipients(self.event, "Guests")


class TestSendCommunication(CommunicationsTestCase):
	def test_queues_one_email_per_guest_with_the_team_reply_to(self):
		frappe.db.set_value("Buzz Team Settings", self.team, "support_email", "help@example.com")
		frappe.clear_document_cache("Buzz Team Settings", self.team)
		issue_ticket(self.event, "a@example.com")
		issue_ticket(self.event, "b@example.com")
		frappe.set_user(self.manager)

		sent = send_communication(self.event, "Guests", "<p>Doors open at 9.</p>", subject="Doors")

		self.assertEqual(sent.recipient_count, 2)
		self.assertEqual(queued_recipients(sent.name), {"a@example.com", "b@example.com"})
		self.assertIn("Reply-To: help@example.com", queued_emails(sent.name)[0].message)

	def test_without_a_support_email_replies_go_to_the_sender(self):
		frappe.db.set_value("Buzz Team Settings", self.team, "support_email", None)
		frappe.clear_document_cache("Buzz Team Settings", self.team)
		issue_ticket(self.event, "c@example.com")
		frappe.set_user(self.manager)

		sent = send_communication(self.event, "Guests", "<p>Hi</p>")

		self.assertIn(f"Reply-To: {self.manager}", queued_emails(sent.name)[0].message)

	def test_a_schedule_lands_on_the_queue_as_send_after(self):
		issue_ticket(self.event, "later@example.com")
		later = add_to_date(now_datetime(), hours=2).replace(microsecond=0)
		frappe.set_user(self.manager)

		sent = send_communication(self.event, "Guests", "<p>Soon.</p>", scheduled_at=later)

		self.assertEqual(sent.scheduled_at, later)
		self.assertEqual(queued_emails(sent.name)[0].send_after, later)

	def test_no_subject_falls_back_to_the_event_title(self):
		issue_ticket(self.event, "titled@example.com")
		frappe.set_user(self.manager)

		sent = send_communication(self.event, "Guests", "<p>Hi</p>")

		title = frappe.db.get_value("Buzz Event", self.event, "title")
		self.assertEqual(sent.subject, "")
		self.assertIn(f"Subject: {title}", queued_emails(sent.name)[0].message)

	def test_nobody_to_send_to_is_refused(self):
		frappe.set_user(self.manager)

		with self.assertRaises(NoRecipients):
			send_communication(self.event, "Speakers", "<p>Hi</p>")

	def test_a_viewer_cannot_send(self):
		issue_ticket(self.event, "v@example.com")
		frappe.set_user(self.viewer)

		with self.assertRaises(CannotSendCommunication):
			send_communication(self.event, "Guests", "<p>Hi</p>")


class TestGetEventCommunications(CommunicationsTestCase):
	def test_lists_what_was_sent_newest_first_with_the_sender(self):
		issue_ticket(self.event, "list@example.com")
		frappe.set_user(self.manager)
		first = send_communication(self.event, "Guests", "<p>One</p>", subject="First")
		second = send_communication(self.event, "Guests", "<p>Two</p>", subject="Second")
		frappe.set_user(self.viewer)

		page = get_event_communications(self.event)

		self.assertEqual([row.name for row in page.communications], [second.name, first.name])
		self.assertEqual(page.communications[0].sent_by, "Manager")
		self.assertFalse(page.can_write)
		self.assertFalse(page.can_edit_settings)

	def test_carries_the_filter_options_and_the_support_email(self):
		frappe.db.set_value("Buzz Team Settings", self.team, "support_email", "team@example.com")
		frappe.clear_document_cache("Buzz Team Settings", self.team)
		issue_ticket(self.event, "opt@example.com")
		frappe.set_user(self.owner)

		page = get_event_communications(self.event)

		self.assertEqual(page.support_email, "team@example.com")
		self.assertTrue(page.ticket_types)
		self.assertIn("Accepted", page.statuses)
		self.assertTrue(page.can_edit_settings)


class TestUpdateSupportEmail(CommunicationsTestCase):
	def test_an_owner_sets_the_team_support_email(self):
		frappe.set_user(self.owner)

		update_support_email(self.event, "reply@example.com")

		self.assertEqual(
			frappe.db.get_value("Buzz Team Settings", self.team, "support_email"), "reply@example.com"
		)

	def test_a_manager_cannot(self):
		frappe.set_user(self.manager)

		with self.assertRaises(CannotEditTeam):
			update_support_email(self.event, "reply@example.com")

	def test_a_bad_address_is_refused(self):
		frappe.set_user(self.owner)

		with self.assertRaises(frappe.InvalidEmailAddressError):
			update_support_email(self.event, "not-an-email")


class TestCommunicationTemplate(CommunicationsTestCase):
	def sent_html(self, **event_values) -> str:
		if event_values:
			frappe.db.set_value("Buzz Event", self.event, event_values)
			frappe.clear_document_cache("Buzz Event", self.event)
		issue_ticket(self.event, "template@example.com")
		frappe.set_user(self.manager)
		sent = send_communication(self.event, "Guests", "<p>Bring a jacket.</p>")
		return html_part(queued_emails(sent.name)[0].message)

	def test_wraps_the_message_in_the_event_header_and_footer(self):
		html = self.sent_html(route=f"comms-{frappe.generate_hash(length=6)}")

		title = frappe.db.get_value("Buzz Event", self.event, "title")
		route = frappe.db.get_value("Buzz Event", self.event, "route")
		self.assertIn(title, html)
		self.assertIn("Bring a jacket.", html)
		self.assertIn("View Event", html)
		self.assertIn(f"/b/register/{route}", html)
		self.assertIn("reply to this email", html)
		self.assertNotIn("Unsubscribe", html)

	def test_shows_the_banner_only_when_the_event_has_one(self):
		self.assertNotIn("data-banner", self.sent_html())

	def test_shows_the_banner_when_the_event_has_one(self):
		html = self.sent_html(banner_image="/files/banner.png")

		self.assertIn("/files/banner.png", html)
