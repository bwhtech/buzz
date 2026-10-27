import frappe
from frappe.utils import add_days, today

from buzz.api.booking import process_booking
from buzz.api.booking.exceptions import ApprovalNeedsFreeTickets, ApprovalRequestPending
from buzz.tasks import expire_pending_approval_requests
from buzz.tests.base_test_cases import ApprovalTestCase
from buzz.tests.factories import (
	EmailTemplateFactory,
	EventTicketFactory,
	EventTicketTypeFactory,
	TicketAddOnFactory,
)
from buzz.tests.utils import queued_booking_emails


def html_of(message) -> str:
	return message.get_body(("html",)).get_content()


class TestApprovalFreeOnlyRule(ApprovalTestCase):
	def setUp(self):
		super().setUp()
		self.set_approval_on(False)

	def set_approval_on(self, enabled: bool):
		frappe.db.set_value(
			"Event Ticket Type", self.approval_ticket_type.name, "requires_approval", int(enabled)
		)
		self.approval_ticket_type.reload()

	def test_approval_cannot_be_turned_on_next_to_a_paid_ticket_type(self):
		EventTicketTypeFactory.create("paid", event=self.event.name)
		ticket_type = EventTicketTypeFactory.create(event=self.event.name)
		ticket_type.requires_approval = 1

		with self.assertRaises(ApprovalNeedsFreeTickets):
			ticket_type.save()

	def test_event_wide_approval_cannot_be_turned_on_next_to_a_paid_ticket_type(self):
		EventTicketTypeFactory.create("paid", event=self.event.name)
		event = frappe.get_doc("Buzz Event", self.event.name)
		event.requires_approval = 1

		with self.assertRaises(ApprovalNeedsFreeTickets):
			event.save()

	def test_approval_cannot_be_turned_on_next_to_a_priced_add_on(self):
		TicketAddOnFactory.create(event=self.event.name, price=200)
		ticket_type = EventTicketTypeFactory.create(event=self.event.name)
		ticket_type.requires_approval = 1

		with self.assertRaises(ApprovalNeedsFreeTickets):
			ticket_type.save()

	def test_a_price_cannot_be_added_to_a_ticket_type_while_approval_is_on(self):
		self.set_approval_on(True)
		self.approval_ticket_type.prices[0].price = 500

		with self.assertRaises(ApprovalNeedsFreeTickets):
			self.approval_ticket_type.save()

	def test_a_paid_ticket_type_cannot_be_added_while_event_wide_approval_is_on(self):
		self.set_event({"requires_approval": 1})

		with self.assertRaises(ApprovalNeedsFreeTickets):
			EventTicketTypeFactory.create("paid", event=self.event.name)

	def test_a_priced_add_on_cannot_be_added_while_a_ticket_type_needs_approval(self):
		self.set_approval_on(True)
		with self.assertRaises(ApprovalNeedsFreeTickets):
			TicketAddOnFactory.create(event=self.event.name, price=200)

	def test_a_free_add_on_is_fine_with_approval_on(self):
		self.set_approval_on(True)
		TicketAddOnFactory.create(event=self.event.name)


class TestApprovalRequest(ApprovalTestCase):
	def request(self, *ticket_types) -> "frappe.Document":
		return frappe.get_doc("Event Booking", self.request_to_join(None, *ticket_types))

	def test_a_request_is_a_draft_without_tickets(self):
		booking = self.request()

		self.assertEqual(
			(booking.docstatus, booking.status, booking.requires_approval), (0, "Approval Pending", 1)
		)
		self.assertEqual(frappe.db.count("Event Ticket", {"booking": booking.name}), 0)
		self.assertEqual(frappe.db.count("Ticket Hold", {"event": self.event.name}), 0)

	def test_the_response_says_the_request_is_pending(self):
		with self.set_user(self.booker):
			payload = process_booking(
				self.booking_request(attendees=self.attendees_for(self.approval_ticket_type.name))
			)

		self.assertTrue(payload.approval_pending)

	def test_a_request_is_accepted_even_when_the_ticket_type_is_sold_out(self):
		ticket_type = EventTicketTypeFactory.create(
			"requires_approval", event=self.event.name, max_tickets_available=1
		)
		EventTicketFactory.create("submitted", event=self.event.name, ticket_type=ticket_type.name)

		self.assertEqual(self.request(ticket_type.name).docstatus, 0)

	def test_the_pending_email_goes_out_with_the_confirmation_email_switched_off(self):
		self.set_event({"send_booking_confirmation_email": 0})

		[message] = queued_booking_emails(self.request().name)

		self.assertIn("is pending", message["Subject"])
		self.assertIn("No ticket has been issued yet", html_of(message))

	def test_event_wide_approval_overrides_the_ticket_types(self):
		self.set_event({"requires_approval": 1})

		booking = self.request(self.free_ticket_type.name)

		self.assertEqual(booking.requires_approval, 1)

	def test_one_approval_ticket_sends_the_whole_booking_to_pending(self):
		booking = self.request(self.free_ticket_type.name, self.approval_ticket_type.name)

		self.assertEqual((booking.docstatus, len(booking.attendees)), (0, 2))

	def test_a_free_ticket_type_needs_no_approval(self):
		booking = self.request(self.free_ticket_type.name)

		self.assertEqual((booking.docstatus, booking.requires_approval), (1, 0))

	def test_a_booking_added_by_an_organizer_skips_approval(self):
		organizer = self.make_organizer()
		attendees = self.attendees_for(self.approval_ticket_type.name)
		with self.set_user(organizer):
			payload = process_booking(self.booking_request(attendees=attendees))

		self.assertFalse(payload.approval_pending)
		self.assertEqual(frappe.db.get_value("Event Booking", payload.booking_name, "docstatus"), 1)

	def test_a_second_pending_request_from_the_same_user_is_refused(self):
		self.request()

		with self.assertRaises(ApprovalRequestPending):
			self.request()

	def test_hosts_are_notified_of_a_request(self):
		organizer = self.make_organizer()

		booking = self.request()

		logs = frappe.get_all(
			"Notification Log",
			filters={"for_user": organizer, "document_type": "Event Booking", "document_name": booking.name},
		)
		self.assertEqual(len(logs), 1)


class TestApprovalDecision(ApprovalTestCase):
	def setUp(self):
		super().setUp()
		self.booking = frappe.get_doc("Event Booking", self.request_to_join())

	def test_approving_issues_tickets_and_confirms(self):
		self.booking.approve_request()
		self.booking.reload()

		self.assertEqual((self.booking.docstatus, self.booking.status), (1, "Confirmed"))
		self.assertEqual(frappe.db.count("Event Ticket", {"booking": self.booking.name}), 1)

	def test_the_approved_email_goes_out_with_the_confirmation_email_switched_off(self):
		self.set_event({"send_booking_confirmation_email": 0})

		self.booking.approve_request()

		[_pending, approved] = queued_booking_emails(self.booking.name)
		self.assertIn("You're in", approved["Subject"])
		self.assertIn("You're in!", html_of(approved))

	def test_the_approved_email_uses_the_custom_confirmation_template(self):
		template = EmailTemplateFactory.create(subject="Custom welcome", response="<p>Custom body</p>")
		self.set_event(
			{"booking_confirmation_email_template": template.name, "send_booking_confirmation_email": 1}
		)

		self.booking.approve_request()

		[_pending, approved] = queued_booking_emails(self.booking.name)
		self.assertEqual(approved["Subject"], "Custom welcome")

	def test_approving_a_sold_out_ticket_type_fails_and_keeps_the_request_pending(self):
		self.approval_ticket_type.max_tickets_available = 1
		self.approval_ticket_type.save()
		EventTicketFactory.create(
			"submitted", event=self.event.name, ticket_type=self.approval_ticket_type.name
		)

		with self.assertRaises(frappe.ValidationError):
			self.booking.approve_request()

		self.booking.reload()
		self.assertEqual((self.booking.docstatus, self.booking.status), (0, "Approval Pending"))

	def test_the_desk_approve_button_goes_through_the_same_path(self):
		self.booking.approve_booking()
		self.booking.reload()

		self.assertEqual((self.booking.docstatus, self.booking.status), (1, "Confirmed"))

	def test_approving_still_works_after_sales_closed(self):
		frappe.db.set_value("Event Ticket Type", self.approval_ticket_type.name, "is_published", 0)

		self.booking.approve_request()

		self.assertEqual(frappe.db.get_value("Event Booking", self.booking.name, "docstatus"), 1)

	def test_a_request_that_now_has_a_price_cannot_be_approved(self):
		ticket_type = str(self.approval_ticket_type.name)
		filters = {"parenttype": "Event Ticket Type", "parent": ticket_type}
		frappe.db.set_value("Buzz Price", filters, "price", 500)
		frappe.clear_document_cache("Event Ticket Type", ticket_type)

		with self.assertRaises(frappe.ValidationError):
			self.booking.approve_request()

		self.assertEqual(frappe.db.get_value("Event Booking", self.booking.name, "docstatus"), 0)

	def test_a_pending_request_cannot_be_submitted_directly(self):
		with self.assertRaises(frappe.ValidationError):
			self.booking.submit()

	def test_declining_discards_and_emails_the_message(self):
		self.booking.decline_request("We are full")
		self.booking.reload()

		self.assertEqual((self.booking.docstatus, self.booking.status), (2, "Rejected"))
		self.assertEqual(self.booking.rejection_reason, "We are full")
		[_pending, declined] = queued_booking_emails(self.booking.name)
		self.assertEqual(declined["Subject"], f"Update on your request to join {self.event.title}")
		self.assertIn("We are full", html_of(declined))

	def test_declining_without_a_message_uses_the_default_text(self):
		self.booking.decline_request()

		[_pending, declined] = queued_booking_emails(self.booking.name)
		self.assertIn("wasn't able to confirm your spot", html_of(declined))

	def test_a_declined_guest_can_request_again(self):
		self.booking.decline_request()

		self.assertEqual(frappe.get_doc("Event Booking", self.request_to_join()).docstatus, 0)


class TestApprovalExpiry(ApprovalTestCase):
	def test_requests_pending_after_the_event_ended_expire_without_an_email(self):
		booking = self.request_to_join()
		emails_before = len(queued_booking_emails(booking))
		self.set_event({"start_date": add_days(today(), -2), "end_date": add_days(today(), -1)})

		expire_pending_approval_requests()

		self.assertEqual(
			frappe.db.get_value("Event Booking", booking, ["docstatus", "status"]), (2, "Expired")
		)
		self.assertEqual(len(queued_booking_emails(booking)), emails_before)

	def test_requests_for_a_live_event_are_left_pending(self):
		booking = self.request_to_join()

		expire_pending_approval_requests()

		self.assertEqual(frappe.db.get_value("Event Booking", booking, "status"), "Approval Pending")
