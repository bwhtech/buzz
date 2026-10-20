from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.playground import download_attachment, get_inbox, reset, start, switch_persona
from buzz.api.playground.exceptions import NotInSandbox, PlaygroundDisabled, UnknownPersona
from buzz.api.playground.services import create_sandbox
from buzz.playground import configure_site
from buzz.playground.cleanup import delete_sandbox
from buzz.tests.factories import EventBookingFactory

PLAYGROUND_CONF = {"buzz_playground": 1, "mute_emails": 1}


class PlaygroundTestCase(IntegrationTestCase):
	def setUp(self):
		self.enterContext(patch.dict(frappe.conf, PLAYGROUND_CONF))
		# Muted mail caches a dummy outgoing account that would outlive the patched conf.
		self.enterContext(patch.object(frappe.local, "outgoing_email_account", {}, create=True))
		self.login_manager = self.enterContext(
			patch.object(frappe.local, "login_manager", MagicMock(), create=True)
		)

	def send(self, sandbox_user: str | None = None, **kwargs) -> "frappe.Document":
		with self.set_user(sandbox_user or "Administrator"):
			# add_css needs built assets, which test benches skip.
			frappe.sendmail(
				recipients=["alice@example.com"],
				subject="Hello",
				message="<p>Hi</p>",
				add_css=False,
				**kwargs,
			)
		return frappe.get_last_doc("Email Queue")

	def emails_of(self, sandbox) -> list[str]:
		return frappe.get_all("Playground Email", {"sandbox": sandbox.name}, pluck="subject")


class TestSandbox(PlaygroundTestCase):
	def test_start_creates_a_seeded_sandbox_and_logs_the_organizer_in(self):
		response = start()

		sandbox = frappe.get_last_doc("Playground Sandbox")
		self.login_manager.login_as.assert_called_once_with(sandbox.organizer)
		self.assertEqual(response.redirect_to, "/b/manage")
		self.assertEqual(frappe.db.count("Buzz Event", {"team": sandbox.team}), 3)
		role = frappe.db.get_value(
			"Buzz Team Membership", {"team": sandbox.team, "user": sandbox.organizer}, "team_role"
		)
		self.assertEqual(role, "Owner")

	def test_seeding_leaves_the_inbox_empty(self):
		sandbox = create_sandbox()
		self.assertEqual(self.emails_of(sandbox), [])

	def test_start_is_not_found_without_the_flag(self):
		frappe.conf.buzz_playground = 0
		with self.assertRaises(PlaygroundDisabled):
			start()

	def test_start_is_not_found_while_email_is_unmuted(self):
		frappe.conf.mute_emails = 0
		with self.assertRaises(PlaygroundDisabled):
			start()

	def test_configure_site_stops_storing_pdfs_on_the_email_queue(self):
		self.addCleanup(frappe.db.set_single_value, "System Settings", "store_attached_pdf_document", 1)
		configure_site()
		self.assertFalse(frappe.db.get_single_value("System Settings", "store_attached_pdf_document"))

	def test_switch_persona_logs_in_that_persona(self):
		sandbox = create_sandbox()
		with self.set_user(sandbox.organizer):
			response = switch_persona("front_desk")
		self.login_manager.login_as.assert_called_once_with(sandbox.front_desk)
		self.assertEqual(response.redirect_to, "/b/check-in")

	def test_reset_moves_the_visitor_to_a_new_sandbox(self):
		sandbox = create_sandbox()
		with self.set_user(sandbox.attendee):
			reset()

		new_sandbox = frappe.get_last_doc("Playground Sandbox")
		self.login_manager.login_as.assert_called_once_with(new_sandbox.organizer)
		self.assertFalse(frappe.db.exists("Playground Sandbox", sandbox.name))

	def test_switch_persona_rejects_an_unknown_persona(self):
		sandbox = create_sandbox()
		with self.set_user(sandbox.organizer), self.assertRaises(UnknownPersona):
			switch_persona("Administrator")

	def test_delete_sandbox_removes_its_team_events_and_users(self):
		sandbox = create_sandbox()
		self.send(sandbox.organizer)

		delete_sandbox(sandbox.name)

		self.assertFalse(frappe.db.exists("Buzz Team", sandbox.team))
		self.assertFalse(frappe.db.exists("Buzz Event", {"team": sandbox.team}))
		self.assertFalse(frappe.db.exists("Playground Email", {"sandbox": sandbox.name}))
		for user in sandbox.personas:
			self.assertFalse(frappe.db.exists("User", user))


class TestInbox(PlaygroundTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		with (
			patch.dict(frappe.conf, PLAYGROUND_CONF),
			patch.object(frappe.local, "outgoing_email_account", {}, create=True),
		):
			cls.sandbox = create_sandbox()
			cls.other_sandbox = create_sandbox()

	def setUp(self):
		super().setUp()
		frappe.db.delete("Playground Email")

	def test_email_sent_by_a_sandbox_user_is_captured_and_never_sent(self):
		queue = self.send(self.sandbox.organizer)

		self.assertEqual(self.emails_of(self.sandbox), ["Hello"])
		self.assertEqual(queue.reload().status, "Cancelled")

	def test_email_about_a_sandbox_event_is_captured_for_that_sandbox(self):
		event = frappe.get_all("Buzz Event", {"team": self.sandbox.team}, pluck="name", limit=1)[0]
		self.send(reference_doctype="Buzz Event", reference_name=event)
		self.assertEqual(self.emails_of(self.sandbox), ["Hello"])

	def test_attachments_are_saved_on_the_captured_email(self):
		self.send(
			self.sandbox.organizer, attachments=[{"fname": "invite.ics", "fcontent": "BEGIN:VCALENDAR"}]
		)

		email = frappe.get_last_doc("Playground Email")
		file_name = frappe.db.get_value("File", {"attached_to_name": email.name}, "file_name")
		self.assertEqual(file_name, "invite.ics")
		self.assertIn("<p>Hi</p>", email.message)

	def test_capture_is_off_without_the_flag(self):
		frappe.conf.buzz_playground = 0
		queue = self.send(self.sandbox.organizer)

		self.assertEqual(self.emails_of(self.sandbox), [])
		self.assertEqual(queue.reload().status, "Not Sent")

	def test_inbox_lists_only_the_sandbox_emails(self):
		self.send(
			self.sandbox.organizer, attachments=[{"fname": "invite.ics", "fcontent": "BEGIN:VCALENDAR"}]
		)
		self.send(self.other_sandbox.organizer)

		with self.set_user(self.sandbox.attendee):
			inbox = get_inbox()

		self.assertEqual([email.recipient for email in inbox], ["alice@example.com"])
		self.assertEqual([attachment.file_name for attachment in inbox[0].attachments], ["invite.ics"])

	def test_attachment_download_is_limited_to_the_sandbox(self):
		self.send(
			self.sandbox.organizer, attachments=[{"fname": "invite.ics", "fcontent": "BEGIN:VCALENDAR"}]
		)
		file = frappe.db.get_value("File", {"attached_to_doctype": "Playground Email"})

		with self.set_user(self.other_sandbox.organizer), self.assertRaises(NotInSandbox):
			download_attachment(file)

		with self.set_user(self.sandbox.front_desk):
			download_attachment(file)
		self.assertEqual(frappe.safe_decode(frappe.local.response.filecontent), "BEGIN:VCALENDAR")

	def test_booking_emails_reach_the_inbox(self):
		event = frappe.get_value(
			"Buzz Event", {"team": self.sandbox.team, "title": "Frontend Meetup"}, "name"
		)
		frappe.db.set_value("Buzz Event", event, "attach_email_ticket", 0)
		ticket_type = frappe.get_value("Event Ticket Type", {"event": event}, "name")
		attendee = {"ticket_type": ticket_type, "first_name": "Sam", "email": self.sandbox.attendee}

		with self.set_user(self.sandbox.attendee):
			booking = EventBookingFactory.create(
				event=event,
				user=self.sandbox.attendee,
				attendees=[attendee],
				flags={"ignore_permissions": True},
			)
			booking.submit()

		subjects = self.emails_of(self.sandbox)
		self.assertEqual(len(subjects), 2)
		self.assertTrue(any("ticket" in subject.lower() for subject in subjects))
