from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz import telemetry
from buzz.api.checkin import checkin_ticket
from buzz.api.forms import submit_event_proposal
from buzz.tests.factories import (
	BuzzEventFactory,
	EventBookingFactory,
	EventTicketTypeFactory,
	SponsorshipEnquiryFactory,
	SponsorshipTierFactory,
	TalkProposalFactory,
)
from buzz.tests.factories.ticketing.event_booking_refund_factory import EventBookingRefundFactory
from buzz.tests.factories.ticketing.ticket_cancellation_request_factory import (
	TicketCancellationRequestFactory,
)
from buzz.tests.telemetry_capture import captured_names, capturing, properties_of
from buzz.www import dashboard

SPONSORSHIP_ENQUIRY = "buzz.proposals.doctype.sponsorship_enquiry.sponsorship_enquiry"


class TestEventTelemetry(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create()

	def test_event_created_from_blank(self):
		with capturing() as mock_capture:
			self.new_event().insert()

		self.assertEqual(
			properties_of(mock_capture, "event_created"),
			{
				**telemetry.shared_properties(),
				"source": "blank",
				"medium": "Online",
				"free_event": False,
				"published": False,
			},
		)
		self.assertNotIn("event_published", captured_names(mock_capture))

	def test_event_published_at_creation(self):
		with capturing() as mock_capture:
			self.new_event(is_published=1).insert()

		self.assertTrue(properties_of(mock_capture, "event_created")["published"])
		self.assertEqual(properties_of(mock_capture, "event_published")["medium"], "Online")

	def test_event_created_from_template(self):
		event = self.new_event()
		event.flags.from_template = True
		with capturing() as mock_capture:
			event.insert()

		self.assertEqual(properties_of(mock_capture, "event_created")["source"], "template")

	def test_event_published_fires_once_when_published(self):
		event = self.new_event().insert()

		with capturing() as mock_capture:
			event.is_published = 1
			event.save()
			event.title = f"{event.title} renamed"
			event.save()

		self.assertEqual(captured_names(mock_capture), ["event_published"])
		self.assertEqual(properties_of(mock_capture, "event_published")["medium"], "Online")

	def test_active_site_for_signed_in_user_only(self):
		with capturing() as mock_capture:
			dashboard.get_context()
		self.assertEqual(captured_names(mock_capture), ["active_site"])
		self.assertEqual(mock_capture.call_args.kwargs["interval"], "1d")

		with self.set_user("Guest"), capturing() as mock_capture:
			dashboard.get_context()
		mock_capture.assert_not_called()

	def new_event(self, **overrides):
		"""Built, not saved, so the insert happens inside the capture."""
		links = {"team": self.event.team, "category": self.event.category, "host": self.event.host}
		return BuzzEventFactory.build("unpublished", medium="Online", **links, **overrides)


class TestBookingTelemetry(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create().name

	def test_booking_confirmed(self):
		with capturing() as mock_capture:
			self.confirmed_booking(attendee_count=2)

		properties = properties_of(mock_capture, "booking_confirmed")
		self.assertEqual(properties["payment"], "free")
		self.assertEqual(properties["attendees"], "2-5")
		self.assertFalse(properties["coupon"])
		self.assertFalse(properties["add_ons"])
		self.assertFalse(properties["utm"])

	def test_booking_draft_sends_nothing(self):
		ticket_type = EventTicketTypeFactory.create(event=self.event).name
		with capturing() as mock_capture:
			EventBookingFactory.create(event=self.event, attendees=self.attendees(ticket_type, 1))

		self.assertNotIn("booking_confirmed", captured_names(mock_capture))

	def test_ticket_checked_in(self):
		booking = self.confirmed_booking()
		ticket = frappe.db.get_value("Event Ticket", {"booking": booking.name}, "name")

		with capturing() as mock_capture:
			checkin_ticket(ticket)

		self.assertEqual(captured_names(mock_capture), ["ticket_checked_in"])

	def test_tickets_cancelled(self):
		booking = self.confirmed_booking(attendee_count=2).name
		ticket = frappe.get_all("Event Ticket", filters={"booking": booking}, pluck="name")[0]
		request = TicketCancellationRequestFactory.create(
			"accepted", booking=booking, tickets=[{"ticket": ticket}]
		)

		with capturing() as mock_capture, patch("frappe.sendmail"):
			request.submit()

		self.assertEqual(
			properties_of(mock_capture, "tickets_cancelled"),
			{**telemetry.shared_properties(), "scope": "tickets", "tickets": "1", "via_refund": False},
		)

	def test_full_booking_cancelled_counts_its_tickets(self):
		booking = self.confirmed_booking(attendee_count=2).name
		request = TicketCancellationRequestFactory.create("accepted", booking=booking, cancel_full_booking=1)

		with capturing() as mock_capture, patch("frappe.sendmail"):
			request.submit()

		properties = properties_of(mock_capture, "tickets_cancelled")
		self.assertEqual((properties["scope"], properties["tickets"]), ("booking", "2-5"))

	def test_booking_refunded_once_when_processed(self):
		ticket_type = EventTicketTypeFactory.create("paid", event=self.event).name
		booking = EventBookingFactory.create(event=self.event, attendees=self.attendees(ticket_type, 1))
		booking.payment_status = "Paid"
		booking.submit()

		with capturing() as mock_capture:
			refund = EventBookingRefundFactory.create(booking=booking.name, amount=booking.total_amount)
			self.assertNotIn("booking_refunded", captured_names(mock_capture))

			refund.status = "Processed"
			refund.save()
			refund.save()

		self.assertEqual(
			properties_of(mock_capture, "booking_refunded"),
			{**telemetry.shared_properties(), "full": True, "covers_tickets": False},
		)

	def confirmed_booking(self, attendee_count: int = 1):
		ticket_type = EventTicketTypeFactory.create(event=self.event).name
		booking = EventBookingFactory.create(
			event=self.event, attendees=self.attendees(ticket_type, attendee_count)
		)
		booking.submit()
		return booking

	def attendees(self, ticket_type: str, count: int) -> list[dict]:
		return [
			{
				"ticket_type": ticket_type,
				"first_name": f"Guest {index}",
				"email": f"telemetry-{index}@example.com",
			}
			for index in range(count)
		]


class TestProposalTelemetry(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create()

	@patch(f"{SPONSORSHIP_ENQUIRY}.SponsorshipEnquiry.send_pitch_deck")
	def test_sponsorship_paid(self, _send_pitch_deck):
		tier = SponsorshipTierFactory.create(event=self.event.name).name
		enquiry = SponsorshipEnquiryFactory.create(event=self.event.name, tier=tier)

		with capturing() as mock_capture, patch(f"{SPONSORSHIP_ENQUIRY}.mark_payment_as_received"):
			enquiry.on_payment_authorized("Failed")
			enquiry.on_payment_authorized("Completed")

		self.assertEqual(captured_names(mock_capture), ["sponsorship_paid"])

	def test_talk_proposal_submitted(self):
		speakers = [{"first_name": "Ada", "email": "ada@example.com"}]
		with capturing() as mock_capture:
			TalkProposalFactory.create(event=self.event.name, speakers=speakers)

		self.assertEqual(properties_of(mock_capture, "talk_proposal_submitted")["speakers"], "1")

	def test_event_proposal_submitted(self):
		self.enterContext(self.change_settings("Buzz Settings", accept_event_proposals=1))
		self.addCleanup(frappe.clear_document_cache, "Buzz Settings", "Buzz Settings")
		with capturing() as mock_capture:
			submit_event_proposal(data=self.event_proposal(medium="In Person"))

		properties = properties_of(mock_capture, "event_proposal_submitted")
		self.assertEqual(properties["medium"], "In Person")
		self.assertFalse(properties["free_event"])

	@patch(f"{SPONSORSHIP_ENQUIRY}.SponsorshipEnquiry.send_pitch_deck")
	def test_sponsorship_enquiry_created(self, _send_pitch_deck):
		with capturing() as mock_capture:
			SponsorshipEnquiryFactory.create(event=self.event.name)

		self.assertEqual(properties_of(mock_capture, "sponsorship_enquiry_created")["tier_selected"], False)

	def event_proposal(self, **values) -> dict:
		return {
			"title": "An event",
			"category": self.event.category,
			"start_date": add_days(today(), 10),
			"start_time": "10:00:00",
			"end_time": "12:00:00",
			"about": "About",
			**values,
		}
