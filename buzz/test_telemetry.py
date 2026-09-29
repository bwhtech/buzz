import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from buzz import telemetry, telemetry_scan
from buzz.api.checkin import checkin_ticket
from buzz.www import dashboard


@contextmanager
def capturing():
	"""Telemetry on, and whatever was captured sent as if the transaction committed."""
	with (
		patch("buzz.telemetry.is_enabled", return_value=True),
		patch("buzz.telemetry.frappe_capture") as mock_capture,
	):
		yield mock_capture
		frappe.db.after_commit.run()


def captured(mock_capture) -> list[tuple[str, dict]]:
	return [(call.args[0], call.kwargs.get("properties", {})) for call in mock_capture.call_args_list]


def captured_names(mock_capture) -> list[str]:
	return [name for name, _properties in captured(mock_capture)]


def properties_of(mock_capture, event: str) -> dict:
	matches = [properties for name, properties in captured(mock_capture) if name == event]
	if len(matches) != 1:
		raise AssertionError(f"expected one {event}, got {captured_names(mock_capture)}")
	return matches[0]


class TestTelemetryWrapper(IntegrationTestCase):
	def test_capture_adds_app_and_shared_properties(self):
		with capturing() as mock_capture:
			telemetry.capture("thing_happened", {"kind": "a"}, interval="1d")

		mock_capture.assert_called_once()
		self.assertEqual(mock_capture.call_args.args, ("thing_happened", "buzz"))
		self.assertEqual(mock_capture.call_args.kwargs["interval"], "1d")
		properties = mock_capture.call_args.kwargs["properties"]
		self.assertEqual(properties["kind"], "a")
		self.assertEqual(properties["app_version"], frappe.get_attr("buzz.__version__"))
		self.assertIn(properties["entry"], {"system", "api", "desk", "dashboard", "website", "import"})

	def test_capture_is_silent_during_system_writes(self):
		for flag in ("in_install", "in_migrate", "in_patch", "in_fixtures"):
			with self.subTest(flag=flag), capturing() as mock_capture:
				frappe.flags[flag] = True
				try:
					telemetry.capture("thing_happened")
				finally:
					frappe.flags[flag] = False
				mock_capture.assert_not_called()

	def test_capture_never_raises(self):
		with (
			patch("buzz.telemetry.is_enabled", return_value=True),
			patch("buzz.telemetry.frappe_capture", side_effect=RuntimeError("pulse down")),
		):
			telemetry.capture("thing_happened")
			frappe.db.after_commit.run()

	def test_rolled_back_capture_is_never_sent(self):
		with capturing() as mock_capture:
			telemetry.capture("thing_happened")
			frappe.db.rollback()
		mock_capture.assert_not_called()

	def test_capture_waits_for_commit(self):
		with (
			patch("buzz.telemetry.is_enabled", return_value=True),
			patch("buzz.telemetry.frappe_capture") as mock_capture,
		):
			telemetry.capture("thing_happened")
			mock_capture.assert_not_called()
			telemetry.capture("page_seen", on_commit=False)
			mock_capture.assert_called_once()
			frappe.db.after_commit.reset()

	def test_entry_from_referrer(self):
		cases = {
			"http://site/app/buzz-event/1": "desk",
			"http://site/b/tickets": "dashboard",
			"http://site/b": "dashboard",
			"http://site/apps/list": "website",
			"http://site/application": "website",
			"http://site/blog/post": "website",
			"http://site/events/my-event": "website",
			"": "api",
		}
		original_request = getattr(frappe.local, "request", None)
		try:
			for referrer, expected in cases.items():
				with self.subTest(referrer=referrer):
					frappe.local.request = SimpleNamespace(headers={"Referer": referrer})
					self.assertEqual(telemetry.get_entry(), expected)
		finally:
			frappe.local.request = original_request

	def test_entry_for_import(self):
		frappe.flags.in_import = True
		try:
			self.assertEqual(telemetry.get_entry(), "import")
		finally:
			frappe.flags.in_import = False

	def test_count_bucket(self):
		cases = {
			0: "0",
			1: "1",
			2: "2-5",
			5: "2-5",
			6: "6-20",
			20: "6-20",
			21: "21-100",
			100: "21-100",
			101: "101+",
		}
		for count, expected in cases.items():
			with self.subTest(count=count):
				self.assertEqual(telemetry.count_bucket(count), expected)


class TestTelemetryEvents(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.test_event = frappe.get_doc("Buzz Event", {"route": "test-route"})

	def setUp(self):
		frappe.set_user("Administrator")

	def new_event(self, **fields):
		return frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"category": self.test_event.category,
				"host": self.test_event.host,
				"team": self.test_event.team,
				"title": f"Telemetry {frappe.generate_hash(length=6)}",
				"start_date": frappe.utils.today(),
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"is_published": 0,
				**fields,
			}
		)

	def free_ticket_type(self):
		return frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.test_event.name,
				"title": f"Telemetry Free {frappe.generate_hash(length=6)}",
				"price": 0,
			}
		).insert()

	def confirmed_booking(self, attendee_count=1):
		ticket_type = self.free_ticket_type()
		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"attendees": [
					{
						"ticket_type": ticket_type.name,
						"first_name": f"Guest {index}",
						"email": f"telemetry-{index}@example.com",
					}
					for index in range(attendee_count)
				],
			}
		).insert()
		booking.submit()
		return booking

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
		ticket_type = self.free_ticket_type()
		with capturing() as mock_capture:
			frappe.get_doc(
				{
					"doctype": "Event Booking",
					"event": self.test_event.name,
					"user": "Administrator",
					"attendees": [
						{"ticket_type": ticket_type.name, "first_name": "Draft", "email": "draft@example.com"}
					],
				}
			).insert()

		self.assertNotIn("booking_confirmed", captured_names(mock_capture))

	def test_ticket_checked_in(self):
		booking = self.confirmed_booking()
		ticket = frappe.db.get_value("Event Ticket", {"booking": booking.name}, "name")

		with capturing() as mock_capture:
			checkin_ticket(ticket)

		self.assertEqual(captured_names(mock_capture), ["ticket_checked_in"])

	def test_tickets_cancelled(self):
		booking = self.confirmed_booking(attendee_count=2)
		tickets = frappe.get_all("Event Ticket", filters={"booking": booking.name}, pluck="name")
		request = frappe.get_doc(
			{
				"doctype": "Ticket Cancellation Request",
				"booking": booking.name,
				"status": "Accepted",
				"tickets": [{"ticket": tickets[0]}],
			}
		).insert()

		with capturing() as mock_capture, patch("frappe.sendmail"):
			request.submit()

		self.assertEqual(
			properties_of(mock_capture, "tickets_cancelled"),
			{**telemetry.shared_properties(), "scope": "tickets", "tickets": "1", "via_refund": False},
		)

	def test_full_booking_cancelled_counts_its_tickets(self):
		booking = self.confirmed_booking(attendee_count=2)
		request = frappe.get_doc(
			{
				"doctype": "Ticket Cancellation Request",
				"booking": booking.name,
				"status": "Accepted",
				"cancel_full_booking": 1,
			}
		).insert()

		with capturing() as mock_capture, patch("frappe.sendmail"):
			request.submit()

		properties = properties_of(mock_capture, "tickets_cancelled")
		self.assertEqual((properties["scope"], properties["tickets"]), ("booking", "2-5"))

	def test_booking_refunded_once_when_processed(self):
		ticket_type = frappe.get_doc(
			{
				"doctype": "Event Ticket Type",
				"event": self.test_event.name,
				"title": f"Telemetry Paid {frappe.generate_hash(length=6)}",
				"price": 100,
			}
		).insert()
		booking = frappe.get_doc(
			{
				"doctype": "Event Booking",
				"event": self.test_event.name,
				"user": "Administrator",
				"attendees": [
					{"ticket_type": ticket_type.name, "first_name": "Paid", "email": "paid@example.com"}
				],
			}
		).insert()
		booking.payment_status = "Paid"
		booking.submit()

		with capturing() as mock_capture:
			refund = frappe.get_doc(
				{
					"doctype": "Event Booking Refund",
					"booking": booking.name,
					"amount": booking.total_amount,
					"status": "Initiated",
					"refund_id": f"rfnd_telemetry_{frappe.generate_hash(length=6)}",
				}
			).insert()
			self.assertNotIn("booking_refunded", captured_names(mock_capture))

			refund.status = "Processed"
			refund.save()
			refund.save()

		self.assertEqual(
			properties_of(mock_capture, "booking_refunded"),
			{**telemetry.shared_properties(), "full": True, "covers_tickets": False},
		)

	def test_sponsorship_paid(self):
		with patch(
			"buzz.proposals.doctype.sponsorship_enquiry.sponsorship_enquiry.SponsorshipEnquiry.send_pitch_deck"
		):
			enquiry = frappe.get_doc(
				{
					"doctype": "Sponsorship Enquiry",
					"event": self.test_event.name,
					"company_name": "Paying Co",
					"company_logo": "/files/paying.png",
					"tier": frappe.db.get_value("Sponsorship Tier", {"event": self.test_event.name}, "name"),
				}
			).insert()

		with (
			capturing() as mock_capture,
			patch("buzz.proposals.doctype.sponsorship_enquiry.sponsorship_enquiry.mark_payment_as_received"),
		):
			enquiry.on_payment_authorized("Failed")
			enquiry.on_payment_authorized("Completed")

		self.assertEqual(captured_names(mock_capture), ["sponsorship_paid"])

	def test_talk_proposal_submitted(self):
		with capturing() as mock_capture:
			frappe.get_doc(
				{
					"doctype": "Talk Proposal",
					"event": self.test_event.name,
					"title": "A talk",
					"speakers": [{"first_name": "Ada", "email": "ada@example.com"}],
				}
			).insert()

		self.assertEqual(properties_of(mock_capture, "talk_proposal_submitted")["speakers"], "1")

	def test_event_proposal_submitted(self):
		with capturing() as mock_capture:
			frappe.get_doc(
				{
					"doctype": "Event Proposal",
					"title": "An event",
					"category": self.test_event.category,
					"start_date": frappe.utils.add_days(frappe.utils.today(), 10),
					"start_time": "10:00:00",
					"end_time": "12:00:00",
					"about": "About",
					"medium": "In Person",
				}
			).insert()

		properties = properties_of(mock_capture, "event_proposal_submitted")
		self.assertEqual(properties["medium"], "In Person")
		self.assertFalse(properties["free_event"])

	def test_sponsorship_enquiry_created(self):
		with (
			capturing() as mock_capture,
			patch(
				"buzz.proposals.doctype.sponsorship_enquiry.sponsorship_enquiry.SponsorshipEnquiry.send_pitch_deck"
			),
		):
			frappe.get_doc(
				{
					"doctype": "Sponsorship Enquiry",
					"event": self.test_event.name,
					"company_name": "Acme",
					"company_logo": "/files/acme.png",
				}
			).insert()

		self.assertEqual(properties_of(mock_capture, "sponsorship_enquiry_created")["tier_selected"], False)

	def test_active_site_for_signed_in_user_only(self):
		with capturing() as mock_capture:
			dashboard.get_context()
		self.assertEqual(captured_names(mock_capture), ["active_site"])
		self.assertEqual(mock_capture.call_args.kwargs["interval"], "1d")

		frappe.set_user("Guest")
		with capturing() as mock_capture:
			dashboard.get_context()
		mock_capture.assert_not_called()


class TestSiteProfile(IntegrationTestCase):
	def test_nothing_is_queried_when_telemetry_is_off(self):
		with (
			patch("buzz.telemetry_scan.is_enabled", return_value=False),
			patch("buzz.telemetry_scan.get_site_profile") as mock_profile,
			capturing() as mock_capture,
		):
			telemetry_scan.send_site_profile()

		mock_profile.assert_not_called()
		mock_capture.assert_not_called()

	def test_site_profile_is_sent_when_telemetry_is_on(self):
		with (
			patch("buzz.telemetry_scan.is_enabled", return_value=True),
			capturing() as mock_capture,
		):
			telemetry_scan.send_site_profile()

		properties = properties_of(mock_capture, "site_profile")
		self.assertGreaterEqual(properties["events"], 1)
		self.assertIn("bookings_per_event_median", properties)
		self.assertIn("payment_gateways", properties)
		self.assertLess(len(json.dumps(properties)), 4096)

	def test_site_profile_values_are_counts_not_names(self):
		profile = telemetry_scan.get_site_profile()
		for key, value in profile.items():
			with self.subTest(key=key):
				self.assertTrue(value is None or isinstance(value, int | float), f"{key}={value!r}")

	def test_missing_table_degrades_to_zero(self):
		with patch("frappe.db.count", side_effect=Exception("table missing")):
			counts = telemetry_scan.get_record_counts()
		self.assertTrue(all(value == 0 for value in counts.values()))
