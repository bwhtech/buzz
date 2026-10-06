import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_datetime, today

from buzz.api.events import get_event_ticket_types, get_verification_methods, set_registration_state
from buzz.api.events.exceptions import CannotManageEvent
from buzz.tests.factories import BuzzEventFactory, BuzzTeamFactory, BuzzTeamMembershipFactory, UserFactory


class RegistrationTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("registration-owner@example.com").name
		cls.viewer = UserFactory.create_once("registration-viewer@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name
		BuzzTeamMembershipFactory.create(team=cls.team, user=cls.viewer, team_role="Viewer")

	def create_event(self, **overrides) -> str:
		return str(BuzzEventFactory.create(team=self.team, **overrides).name)

	def registration_as(self, user: str, event: str):
		with self.set_user(user):
			return get_event_ticket_types(event)


class TestSetRegistrationState(RegistrationTestCase):
	def test_closing_stops_registrations_now_in_the_events_own_timezone(self):
		"""A UTC wall clock would sit hours ahead of an event west of UTC, leaving it open."""
		event = self.create_event(time_zone="US/Pacific")

		with self.set_user(self.owner):
			self.assertTrue(set_registration_state(event, closed=True).registrations_closed)
		self.assertTrue(self.registration_as(self.owner, event).registrations_closed)

	def test_opening_clears_the_cutoff(self):
		event = self.create_event(registrations_close_at=days_from_now(-30))

		with self.set_user(self.owner):
			self.assertFalse(set_registration_state(event, closed=False).registrations_closed)
		self.assertIsNone(frappe.db.get_value("Buzz Event", event, "registrations_close_at"))

	def test_an_ended_event_stays_closed_when_it_is_opened(self):
		"""Clearing the cutoff cannot reopen it, so the answer says closed rather than done."""
		event = self.create_event(start_date=add_days(today(), -10), end_date=add_days(today(), -9))

		with self.set_user(self.owner):
			self.assertTrue(set_registration_state(event, closed=False).registrations_closed)

	def test_a_reader_cannot_change_the_registration_state(self):
		event = self.create_event()

		with self.set_user(self.viewer), self.assertRaises(CannotManageEvent):
			set_registration_state(event, closed=True)

	def test_the_registration_page_tells_a_reader_they_cannot_write(self):
		event = self.create_event()

		self.assertFalse(self.registration_as(self.viewer, event).can_write)
		self.assertTrue(self.registration_as(self.owner, event).can_write)

	def test_an_external_registration_page_is_linked_instead_of_the_buzz_one(self):
		event = self.create_event(
			external_registration_page=1, registration_url="https://tickets.example.com/buzz"
		)

		link = self.registration_as(self.owner, event).registration_link

		self.assertEqual(link, "https://tickets.example.com/buzz")

	def test_an_ordinary_event_is_linked_to_its_own_registration_page(self):
		route = f"hosted-{frappe.generate_hash(length=8)}"
		event = self.create_event(route=route)

		self.assertEqual(self.registration_as(self.owner, event).registration_link, f"/b/register/{route}")


class TestRegistrationSettings(RegistrationTestCase):
	def test_carries_the_guest_registration_settings(self):
		event = self.create_event()
		# Written through the db: validate refuses Phone OTP while SMS is not configured.
		guest_booking = {"allow_guest_booking": 1, "guest_verification_method": "Phone OTP"}
		frappe.db.set_value("Buzz Event", event, guest_booking)

		registration = self.registration_as(self.owner, event)

		self.assertTrue(registration.allow_guest_booking)
		self.assertEqual(registration.guest_verification_method, "Phone OTP")

	def test_carries_the_tax_settings(self):
		event = self.create_event()
		tax = {"apply_tax": 1, "tax_inclusive": 1, "tax_label": "VAT", "tax_percentage": 20}
		frappe.db.set_value("Buzz Event", event, tax)

		registration = self.registration_as(self.owner, event)

		self.assertTrue(registration.apply_tax)
		self.assertTrue(registration.tax_inclusive)
		self.assertEqual((registration.tax_label, registration.tax_percentage), ("VAT", 20))

	def test_tax_settings_fall_back_to_gst_defaults(self):
		event = self.create_event()
		frappe.db.set_value("Buzz Event", event, {"tax_label": None, "tax_percentage": 0})

		registration = self.registration_as(self.owner, event)

		self.assertFalse(registration.apply_tax)
		self.assertEqual((registration.tax_label, registration.tax_percentage), ("GST", 18))

	def test_reports_registrations_closed_once_the_cutoff_has_passed(self):
		event = self.create_event(registrations_close_at=days_from_now(-30))

		self.assertTrue(self.registration_as(self.owner, event).registrations_closed)

	def test_a_new_event_starts_with_registrations_closed(self):
		self.assertTrue(self.registration_as(self.owner, self.create_event()).registrations_closed)

	def test_a_cutoff_given_at_creation_is_kept(self):
		close_at = days_from_now(60)
		event = self.create_event(registrations_close_at=close_at)

		saved = frappe.db.get_value("Buzz Event", event, "registrations_close_at")
		self.assertEqual(get_datetime(saved), get_datetime(close_at))

	def test_a_duplicated_event_starts_with_registrations_closed(self):
		source = frappe.get_doc("Buzz Event", self.create_event(registrations_close_at=days_from_now(60)))
		duplicate = frappe.copy_doc(source, ignore_no_copy=False).insert(ignore_permissions=True)

		self.assertTrue(self.registration_as(self.owner, str(duplicate.name)).registrations_closed)

	def test_reports_registrations_open_before_the_event_ends(self):
		event = self.create_event()
		frappe.db.set_value("Buzz Event", event, "registrations_close_at", None)

		self.assertFalse(self.registration_as(self.owner, event).registrations_closed)


class TestVerificationMethods(IntegrationTestCase):
	"""Site configuration, so every case here writes SMS Settings rather than an event."""

	def setUp(self):
		# Cleanups run last-registered-first, so the cache is cleared after the rollback:
		# the Single is cached per request and would otherwise be read back undone.
		self.addCleanup(frappe.clear_document_cache, "SMS Settings", "SMS Settings")
		self.addCleanup(frappe.db.rollback)

	def test_phone_needs_a_gateway(self):
		# Written through the db: an unconfigured Single cannot pass its own mandatory check.
		frappe.db.set_single_value("SMS Settings", "sms_gateway_url", "")

		self.assertFalse(get_verification_methods().phone)

	def test_phone_needs_the_guest_role_to_be_allowed(self):
		settings = frappe.get_single("SMS Settings")
		settings.sms_gateway_url = "https://sms.example.com/send"
		settings.message_parameter = "message"
		settings.receiver_parameter = "to"
		settings.set("allowed_roles", [{"role": "System Manager"}])
		settings.save()

		self.assertFalse(get_verification_methods().phone)

		settings.append("allowed_roles", {"role": "Guest"})
		settings.save()

		self.assertTrue(get_verification_methods().phone)

	def test_email_follows_the_outgoing_account(self):
		# Whatever this site is configured with, the answer is what frappe.sendmail resolves.
		from frappe.email.doctype.email_account.email_account import EmailAccount

		self.assertEqual(get_verification_methods().email, bool(EmailAccount.find_default_outgoing()))


def days_from_now(days: int) -> str:
	return f"{add_days(today(), days)} 00:00:00"
