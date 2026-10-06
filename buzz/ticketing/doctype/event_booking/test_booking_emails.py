from unittest.mock import patch

import frappe

from buzz.tests.base_test_cases import BookingTestCase
from buzz.tests.factories import (
	BuzzTeamFactory,
	EmailTemplateFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
	UserFactory,
)

OFFLINE_METHOD = "Bank Transfer"


class BookingEmailTestCase(BookingTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.email_booker = UserFactory.create_once("booking-email-booker@example.com").name
		cls.ticket_type = EventTicketTypeFactory.create(
			event=cls.event.name, title="Email Ticket", prices=[{"currency": "INR", "price": 100}]
		)

	def setUp(self):
		super().setUp()
		# Ticket emails stay off, so `frappe.sendmail` only sees the booking email.
		self.set_event(
			{
				"apply_tax": 0,
				"send_ticket_email": 0,
				"send_booking_confirmation_email": 1,
				"booking_confirmation_email_template": None,
				"offline_acknowledgement_email_template": None,
			}
		)
		BuzzTeamFactory.set_settings(
			self.event.team, {"default_booking_confirmation_email_template": None, "support_email": None}
		)

	def create_booking(self, user: str, **overrides):
		attendees = [
			{"ticket_type": self.ticket_type.name, "first_name": "John", "email": "john@example.com"}
		]
		return EventBookingFactory.create(event=self.event.name, user=user, attendees=attendees, **overrides)

	def create_template(self, subject_prefix: str) -> str:
		return EmailTemplateFactory.create(subject=f"{subject_prefix} - {{{{ event_title }}}}").name

	def set_team_template(self, template: str | None):
		BuzzTeamFactory.set_settings(
			self.event.team, {"default_booking_confirmation_email_template": template}
		)


@patch("frappe.sendmail")
class TestBookingConfirmationEmail(BookingEmailTestCase):
	def test_sends_confirmation_to_booker(self, sendmail):
		booking = self.submit_booking()

		sendmail.assert_called_once()
		self.assertIn(self.email_booker, sendmail.call_args[1]["recipients"])
		self.assertEqual(sendmail.call_args[1]["reference_doctype"], "Event Booking")
		self.assertEqual(sendmail.call_args[1]["reference_name"], booking.name)

	def test_uses_inline_template_when_none_configured(self, sendmail):
		self.submit_booking()

		self.assertEqual(sendmail.call_args[1]["template"], "booking_confirmation")

	def test_skips_administrator(self, sendmail):
		self.submit_booking("Administrator")

		sendmail.assert_not_called()

	def test_skips_guest(self, sendmail):
		self.submit_booking("Guest")

		sendmail.assert_not_called()

	def test_respects_event_toggle_off(self, sendmail):
		self.set_event({"send_booking_confirmation_email": 0})

		self.submit_booking()

		sendmail.assert_not_called()

	def test_uses_event_template_when_set(self, sendmail):
		self.set_event({"booking_confirmation_email_template": self.create_template("EVENT")})

		self.submit_booking()

		self.assertIn("EVENT", sendmail.call_args[1]["subject"])

	def test_falls_back_to_the_teams_default_template(self, sendmail):
		self.set_team_template(self.create_template("TEAM"))

		self.submit_booking()

		self.assertIn("TEAM", sendmail.call_args[1]["subject"])

	def test_support_email_comes_from_the_teams_settings(self, sendmail):
		BuzzTeamFactory.set_settings(self.event.team, {"support_email": "booking-support@example.com"})

		self.submit_booking()

		self.assertEqual(sendmail.call_args[1]["args"]["support_email"], "booking-support@example.com")

	def test_event_template_takes_precedence_over_the_team_default(self, sendmail):
		self.set_event({"booking_confirmation_email_template": self.create_template("EVENT")})
		self.set_team_template(self.create_template("TEAM"))

		self.submit_booking()

		sendmail.assert_called_once()
		self.assertIn("EVENT", sendmail.call_args[1]["subject"])
		self.assertNotIn("TEAM", sendmail.call_args[1]["subject"])

	def submit_booking(self, user: str | None = None):
		booking = self.create_booking(user or self.email_booker)
		booking.submit()
		return booking


class TestOfflineAcknowledgementEmail(BookingEmailTestCase):
	"""Sent when an offline booking is created, before the payment is verified."""

	@patch("frappe.sendmail")
	def test_sends_acknowledgement_to_booker(self, sendmail):
		booking = self.acknowledge()

		sendmail.assert_called_once()
		self.assertIn(self.email_booker, sendmail.call_args[1]["recipients"])
		self.assertEqual(sendmail.call_args[1]["reference_doctype"], "Event Booking")
		self.assertEqual(sendmail.call_args[1]["reference_name"], booking.name)

	@patch("frappe.sendmail")
	def test_uses_inline_template_when_none_configured(self, sendmail):
		self.acknowledge()

		self.assertEqual(sendmail.call_args[1]["template"], "offline_booking_acknowledgement")

	@patch("frappe.sendmail")
	def test_carries_the_booking_summary(self, sendmail):
		booking = self.acknowledge()

		args = sendmail.call_args[1]["args"]
		self.assertEqual(args["doc"].name, booking.name)
		self.assertEqual(args["event_title"], self.event.title)
		# Ticket types autoname to integers and arrive off the row as strings.
		self.assertEqual([row["ticket_type_title"] for row in args["attendee_rows"]], ["Email Ticket"])

	def test_builtin_template_renders(self):
		# Every other test mocks the send, so only this one catches a broken Jinja tag.
		booking = self.create_offline_booking(self.email_booker)

		html = frappe.render_template(
			"templates/emails/offline_booking_acknowledgement.html", booking.get_booking_email_args()
		)

		for text in ("Payment verification pending", booking.name, OFFLINE_METHOD, "Email Ticket"):
			self.assertIn(text, html)

	@patch("frappe.sendmail")
	def test_uses_event_template_when_set(self, sendmail):
		self.set_event({"offline_acknowledgement_email_template": self.create_template("OFFLINE")})

		self.acknowledge()

		self.assertIn("OFFLINE", sendmail.call_args[1]["subject"])

	@patch("frappe.sendmail")
	def test_ignores_the_confirmation_template(self, sendmail):
		# The acknowledgement has its own template field; the confirmation's must not leak in.
		self.set_event({"booking_confirmation_email_template": self.create_template("EVENT")})
		self.set_team_template(self.create_template("TEAM"))

		self.acknowledge()

		self.assertEqual(sendmail.call_args[1]["template"], "offline_booking_acknowledgement")

	@patch("frappe.sendmail")
	def test_respects_event_toggle_off(self, sendmail):
		self.set_event({"send_booking_confirmation_email": 0})

		self.acknowledge()

		sendmail.assert_not_called()

	@patch("frappe.sendmail")
	def test_skips_system_users(self, sendmail):
		for user in ("Administrator", "Guest"):
			with self.subTest(user=user):
				self.acknowledge(user)

		sendmail.assert_not_called()

	def create_offline_booking(self, user: str):
		"""The draft `offline_booking_response` leaves behind: awaiting verification, no tickets."""
		return self.create_booking(
			user,
			payment_method="Offline",
			offline_payment_method=OFFLINE_METHOD,
			status="Approval Pending",
			payment_status="Verification Pending",
		)

	def acknowledge(self, user: str | None = None):
		booking = self.create_offline_booking(user or self.email_booker)
		booking.send_offline_acknowledgement_email()
		return booking
