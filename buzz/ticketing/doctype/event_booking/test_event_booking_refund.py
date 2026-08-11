# Copyright (c) 2026, BWH Studios and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz.payments import handle_refund_notification

TICKET_PRICE = 500
TAX_PERCENTAGE = 10
CHARGED_PER_TICKET = 550.0


def make_payment_gateway(gateway: str) -> None:
	if not frappe.db.exists("Payment Gateway", gateway):
		frappe.get_doc({"doctype": "Payment Gateway", "gateway": gateway}).insert()


class BookingRefundTestCase(IntegrationTestCase):
	def setUp(self):
		self.event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self.event.apply_tax = 1
		self.event.tax_inclusive = 0
		self.event.tax_percentage = TAX_PERCENTAGE
		self.event.tax_label = "GST"
		self.event.save()

		self.ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.event.name,
				"title": "Refundable",
				"price": TICKET_PRICE,
				"is_published": True,
			}
		).insert()

		self.booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": self.ticket_type.name, "first_name": "John", "email": "john@example.com"},
					{
						"ticket_type": self.ticket_type.name,
						"first_name": "Jenny",
						"email": "jenny@example.com",
					},
				],
			}
		).insert()
		self.booking.payment_status = "Paid"
		self.booking.submit()

	def refund_id(self, suffix: str = "1") -> str:
		"""Refund ids are unique in the database, so keep them unique per test too."""
		return f"rfnd_{self._testMethodName}_{suffix}"

	def refunds(self) -> list:
		return [
			frappe.get_doc("Event Booking Refund", refund.name)
			for refund in frappe.get_all(
				"Event Booking Refund", filters={"booking": self.booking.name}, order_by="creation asc"
			)
		]

	def make_payment(self, gateway: str = "Razorpay", payment_id: str = "pay_123") -> None:
		make_payment_gateway(gateway)
		frappe.get_doc(
			{
				"doctype": "Event Payment",
				"user": "Administrator",
				"amount": self.booking.total_amount,
				"currency": self.booking.currency,
				"reference_doctype": "Event Booking",
				"reference_docname": self.booking.name,
				"payment_gateway": gateway,
				"payment_received": 1,
				"payment_id": payment_id,
			}
		).insert()


class TestRefundSummary(BookingRefundTestCase):
	def test_each_ticket_carries_its_share_of_the_charged_total(self):
		# 500 + 500 booked, 10% tax on top, so each ticket cost the buyer 550.
		summary = self.booking.get_refund_summary()

		self.assertEqual(len(summary["tickets"]), 2)
		self.assertEqual([ticket["amount"] for ticket in summary["tickets"]], [550.0, 550.0])

	def test_tickets_are_named_and_linked_to_their_attendee(self):
		summary = self.booking.get_refund_summary()

		self.assertTrue(all(ticket["ticket"] for ticket in summary["tickets"]))
		self.assertEqual(
			sorted(ticket["attendee"] for ticket in summary["tickets"]),
			["Jenny", "John"],
		)

	def test_the_whole_total_is_refundable_before_any_refund(self):
		summary = self.booking.get_refund_summary()

		self.assertEqual(summary["committed"], 0)
		self.assertEqual(summary["remaining"], self.booking.total_amount)


class TestBookingRefund(BookingRefundTestCase):
	def refund(self, **kwargs):
		client = MagicMock()
		client.refund_payment.return_value = {
			"id": kwargs.pop("refund_id", self.refund_id()),
			"status": "pending",
			"amount": int(kwargs.get("amount", CHARGED_PER_TICKET) * 100),
		}

		with patch("buzz.ticketing.doctype.event_booking.event_booking.get_controller", return_value=client):
			result = self.booking.refund(**kwargs)

		self.booking.reload()
		return result, client

	def test_refund_is_refused_when_the_gateway_is_not_razorpay(self):
		self.make_payment(gateway="PayPal")

		with self.assertRaises(frappe.ValidationError) as raised:
			self.booking.refund(amount=100)

		self.assertIn("Razorpay", str(raised.exception))

	def test_refund_is_refused_without_a_received_payment(self):
		self.assertRaises(frappe.ValidationError, self.booking.refund, amount=100)

	def test_refunding_tickets_records_the_refund_and_marks_it_initiated(self):
		self.make_payment()
		tickets = self.booking.get_refund_summary()["tickets"]

		_, client = self.refund(amount=CHARGED_PER_TICKET, tickets=[tickets[0]["ticket"]])

		client.refund_payment.assert_called_once_with("pay_123", CHARGED_PER_TICKET)
		self.assertEqual(self.booking.refund_status, "Refund Initiated")
		self.assertEqual(len(self.refunds()), 1)
		self.assertEqual(self.refunds()[0].refund_id, self.refund_id())
		self.assertEqual(self.refunds()[0].status, "Initiated")
		self.assertEqual(self.refunds()[0].amount, CHARGED_PER_TICKET)

	def test_refunding_tickets_queues_a_cancellation_request_for_them(self):
		self.make_payment()
		tickets = self.booking.get_refund_summary()["tickets"]

		self.refund(amount=CHARGED_PER_TICKET, tickets=[tickets[0]["ticket"]])

		request = frappe.get_doc("Ticket Cancellation Request", self.refunds()[0].cancellation_request)
		self.assertEqual(request.docstatus, 0)
		self.assertEqual(request.status, "In Review")
		self.assertEqual([row.ticket for row in request.tickets], [tickets[0]["ticket"]])

	def test_a_ticket_from_another_booking_is_refused(self):
		self.make_payment()
		stranger = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event.name,
				"user": "Administrator",
				"attendees": [
					{
						"ticket_type": self.ticket_type.name,
						"first_name": "Stranger",
						"email": "stranger@example.com",
					}
				],
			}
		).insert()
		stranger.payment_status = "Paid"
		stranger.submit()
		foreign_ticket = frappe.db.get_value("Event Ticket", {"booking": stranger.name}, "name")

		# Patch the gateway so nothing but the ownership check can refuse this.
		with self.assertRaises(frappe.ValidationError):
			self.refund(amount=CHARGED_PER_TICKET, tickets=[foreign_ticket])

		self.assertFalse(frappe.db.exists("Ticket Cancellation Request", {"booking": self.booking.name}))
		self.assertEqual(frappe.db.get_value("Event Ticket", foreign_ticket, "docstatus"), 1)

	def test_a_custom_amount_refund_cancels_no_tickets(self):
		self.make_payment()

		self.refund(amount=100)

		self.assertIsNone(self.refunds()[0].cancellation_request)
		self.assertFalse(frappe.db.exists("Ticket Cancellation Request", {"booking": self.booking.name}))


class TestRefundNotification(BookingRefundTestCase):
	def setUp(self):
		super().setUp()
		self.make_payment()

	def notify(self, refund_id: str, status: str, amount: float) -> None:
		# Cancelling a ticket emails the attendee, and the test site has no
		# outgoing account. Delivery is not what these tests are about.
		log = frappe.get_doc(
			{
				"doctype": "Integration Request",
				"integration_request_service": "Razorpay",
				"request_description": "Refund Notification",
				"is_remote_request": 1,
				"status": "Queued",
				"data": frappe.as_json(
					{
						"event": f"refund.{status}",
						"payload": {
							"refund": {
								"entity": {
									"id": refund_id,
									"status": status,
									"amount": int(amount * 100),
									"payment_id": "pay_123",
								}
							}
						},
					}
				),
			}
		).insert(ignore_permissions=True)

		with patch("frappe.sendmail"):
			handle_refund_notification("Integration Request", log.name)

		self.booking.reload()
		return log

	def initiate(self, refund_id: str, amount: float, tickets: list[str] | None = None) -> None:
		client = MagicMock()
		client.refund_payment.return_value = {
			"id": refund_id,
			"status": "pending",
			"amount": int(amount * 100),
		}

		with patch("buzz.ticketing.doctype.event_booking.event_booking.get_controller", return_value=client):
			self.booking.refund(amount=amount, tickets=tickets)

		self.booking.reload()

	def test_a_processed_refund_covering_the_total_marks_the_booking_refunded(self):
		self.initiate(self.refund_id("1"), self.booking.total_amount)

		self.notify(self.refund_id("1"), "processed", self.booking.total_amount)

		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual(self.booking.refunded_amount, self.booking.total_amount)
		self.assertEqual(self.refunds()[0].status, "Processed")

	def test_a_processed_refund_below_the_total_marks_the_booking_partially_refunded(self):
		self.initiate(self.refund_id("1"), CHARGED_PER_TICKET)

		self.notify(self.refund_id("1"), "processed", CHARGED_PER_TICKET)

		self.assertEqual(self.booking.refund_status, "Partially Refunded")
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)

	def test_the_same_event_arriving_twice_is_not_counted_twice(self):
		self.initiate(self.refund_id("1"), CHARGED_PER_TICKET)

		self.notify(self.refund_id("1"), "processed", CHARGED_PER_TICKET)
		self.notify(self.refund_id("1"), "processed", CHARGED_PER_TICKET)

		self.assertEqual(len(self.refunds()), 1)
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)

	def test_a_failed_refund_is_not_counted_and_drops_its_queued_cancellation(self):
		tickets = self.booking.get_refund_summary()["tickets"]
		self.initiate(self.refund_id("1"), CHARGED_PER_TICKET, tickets=[tickets[0]["ticket"]])
		cancellation_request = self.refunds()[0].cancellation_request

		self.notify(self.refund_id("1"), "failed", CHARGED_PER_TICKET)

		self.assertEqual(self.refunds()[0].status, "Failed")
		self.assertEqual(self.booking.refunded_amount, 0)
		self.assertEqual(
			frappe.db.get_value("Ticket Cancellation Request", cancellation_request, "status"), "Rejected"
		)

	def test_a_webhook_processed_as_guest_still_updates_the_booking(self):
		# The refund webhook is an allow_guest endpoint, so the job it enqueues
		# runs as Guest — who has no write permission on Event Booking.
		tickets = self.booking.get_refund_summary()["tickets"]
		self.initiate(self.refund_id("1"), CHARGED_PER_TICKET, tickets=[tickets[0]["ticket"]])
		cancellation_request = self.refunds()[0].cancellation_request
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")

		self.notify(self.refund_id("1"), "processed", CHARGED_PER_TICKET)

		self.assertEqual(self.refunds()[0].status, "Processed")
		self.assertEqual(self.booking.refund_status, "Partially Refunded")
		self.assertEqual(
			frappe.db.get_value("Ticket Cancellation Request", cancellation_request, "docstatus"), 1
		)

	def test_a_processed_refund_accepts_and_submits_the_queued_cancellation(self):
		tickets = self.booking.get_refund_summary()["tickets"]
		self.initiate(self.refund_id("1"), CHARGED_PER_TICKET, tickets=[tickets[0]["ticket"]])
		cancellation_request = self.refunds()[0].cancellation_request

		self.notify(self.refund_id("1"), "processed", CHARGED_PER_TICKET)

		request = frappe.get_doc("Ticket Cancellation Request", cancellation_request)
		self.assertEqual(request.status, "Accepted")
		self.assertEqual(request.docstatus, 1)
		self.assertEqual(frappe.db.get_value("Event Ticket", tickets[0]["ticket"], "docstatus"), 2)

	def test_a_cancellation_that_cannot_go_through_leaves_the_refund_recorded(self):
		tickets = self.booking.get_refund_summary()["tickets"]
		self.initiate(self.refund_id("1"), CHARGED_PER_TICKET, tickets=[tickets[0]["ticket"]])
		refund = self.refunds()[0]
		cancellation_request = refund.cancellation_request

		with patch("frappe.sendmail", side_effect=Exception("no outgoing email account")):
			refund.apply_gateway_status("processed", CHARGED_PER_TICKET)

		self.booking.reload()
		self.assertEqual(self.refunds()[0].status, "Processed")
		self.assertEqual(self.booking.refunded_amount, CHARGED_PER_TICKET)

		request = frappe.get_doc("Ticket Cancellation Request", cancellation_request)
		self.assertEqual(request.docstatus, 0)
		self.assertEqual(request.status, "In Review")
		self.assertEqual(frappe.db.get_value("Event Ticket", tickets[0]["ticket"], "docstatus"), 1)

	def test_the_integration_request_is_linked_back_to_the_booking(self):
		self.initiate(self.refund_id("1"), CHARGED_PER_TICKET)

		log = self.notify(self.refund_id("1"), "processed", CHARGED_PER_TICKET)

		self.assertEqual(
			frappe.db.get_value("Integration Request", log.name, "reference_docname"), self.booking.name
		)

	def test_a_refund_for_an_unknown_payment_is_ignored(self):
		log = frappe.get_doc(
			{
				"doctype": "Integration Request",
				"integration_request_service": "Razorpay",
				"request_description": "Refund Notification",
				"is_remote_request": 1,
				"status": "Queued",
				"data": frappe.as_json(
					{
						"event": "refund.processed",
						"payload": {
							"refund": {"entity": {"id": self.refund_id("x"), "payment_id": "pay_nope"}}
						},
					}
				),
			}
		).insert(ignore_permissions=True)

		self.assertIsNone(handle_refund_notification("Integration Request", log.name))
		self.booking.reload()
		self.assertFalse(self.refunds())


class TestRefundCeiling(IntegrationTestCase):
	"""A booking of 2000 + 3000 must never give back more than 5000."""

	def setUp(self):
		self.event = frappe.get_doc("Buzz Event", {"route": "test-route"})
		self.event.apply_tax = 0
		self.event.save()

		self.ticket_types = [
			frappe.get_doc(
				{
					"doctype": "Event Ticket Type",
					"event": self.event.name,
					"title": f"Tier {price}",
					"price": price,
					"is_published": True,
				}
			).insert()
			for price in (2000, 3000)
		]

		self.booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.event.name,
				"user": "Administrator",
				"attendees": [
					{
						"ticket_type": self.ticket_types[0].name,
						"first_name": "Cheap",
						"email": "cheap@example.com",
					},
					{
						"ticket_type": self.ticket_types[1].name,
						"first_name": "Pricey",
						"email": "pricey@example.com",
					},
				],
			}
		).insert()
		self.booking.payment_status = "Paid"
		self.booking.submit()

		make_payment_gateway("Razorpay")
		frappe.get_doc(
			{
				"doctype": "Event Payment",
				"user": "Administrator",
				"amount": self.booking.total_amount,
				"currency": self.booking.currency,
				"reference_doctype": "Event Booking",
				"reference_docname": self.booking.name,
				"payment_gateway": "Razorpay",
				"payment_received": 1,
				"payment_id": "pay_123",
			}
		).insert()

	def refund_id(self, suffix: str = "1") -> str:
		"""Refund ids are unique in the database, so keep them unique per test too."""
		return f"rfnd_{self._testMethodName}_{suffix}"

	def refund(self, amount: float, refund_id: str | None = None, tickets: list[str] | None = None):
		refund_id = refund_id or self.refund_id()
		client = MagicMock()
		client.refund_payment.return_value = {
			"id": refund_id,
			"status": "pending",
			"amount": int(amount * 100),
		}

		with patch("buzz.ticketing.doctype.event_booking.event_booking.get_controller", return_value=client):
			return self.booking.refund(amount=amount, tickets=tickets)

	def settle(self, refund_id: str, amount: float) -> None:
		refund = frappe.get_doc("Event Booking Refund", {"refund_id": refund_id})
		with patch("frappe.sendmail"):
			refund.apply_gateway_status("processed", amount)

		self.booking.reload()

	def test_the_booking_total_is_the_ceiling(self):
		self.assertEqual(self.booking.total_amount, 5000)

	def test_a_second_refund_cannot_exceed_what_is_left_after_a_settled_one(self):
		self.refund(3000, refund_id=self.refund_id("1"))
		self.settle(self.refund_id("1"), 3000)

		with self.assertRaises(frappe.ValidationError) as raised:
			self.refund(3000, refund_id=self.refund_id("2"))

		self.assertIn("2,000", str(raised.exception))

	def test_a_second_refund_cannot_exceed_what_is_left_while_the_first_is_still_initiated(self):
		# The gateway has not settled the first refund yet, so it cannot be relied
		# on to reject the second one either.
		self.refund(3000, refund_id=self.refund_id("1"))

		self.assertRaises(frappe.ValidationError, self.refund, 3000, self.refund_id("2"))

	def test_a_failed_refund_frees_its_amount_again(self):
		self.refund(3000, refund_id=self.refund_id("1"))
		frappe.get_doc("Event Booking Refund", {"refund_id": self.refund_id("1")}).apply_gateway_status(
			"failed", 3000
		)
		self.booking.reload()

		self.refund(3000, refund_id=self.refund_id("2"))

		self.assertEqual(len(frappe.get_all("Event Booking Refund", {"booking": self.booking.name})), 2)

	def test_refunding_exactly_what_is_left_is_allowed(self):
		self.refund(3000, refund_id=self.refund_id("1"))
		self.settle(self.refund_id("1"), 3000)

		self.refund(2000, refund_id=self.refund_id("2"))
		self.settle(self.refund_id("2"), 2000)

		self.assertEqual(self.booking.refund_status, "Refunded")
		self.assertEqual(self.booking.refunded_amount, 5000)

	def test_a_ticket_already_refunded_is_not_offered_again(self):
		tickets = self.booking.get_refund_summary()["tickets"]
		self.refund(3000, refund_id=self.refund_id("1"), tickets=[tickets[1]["ticket"]])
		self.settle(self.refund_id("1"), 3000)

		remaining = self.booking.get_refund_summary()

		self.assertEqual([ticket["ticket"] for ticket in remaining["tickets"]], [tickets[0]["ticket"]])
		self.assertEqual(remaining["remaining"], 2000)

	def test_a_ticket_whose_refund_failed_is_offered_again(self):
		tickets = self.booking.get_refund_summary()["tickets"]
		self.refund(3000, refund_id=self.refund_id("1"), tickets=[tickets[1]["ticket"]])

		frappe.get_doc("Event Booking Refund", {"refund_id": self.refund_id("1")}).apply_gateway_status(
			"failed", 3000
		)
		self.booking.reload()

		self.assertEqual(len(self.booking.get_refund_summary()["tickets"]), 2)
