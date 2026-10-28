import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_datetime, now_datetime

from buzz.patches.move_registration_questions_to_buzz_form import execute
from buzz.tests.factories import BuzzEventFactory

REGISTRATION_DOCTYPES = ["Event Booking", "Event Booking Attendee"]


class TestMoveRegistrationQuestionsToBuzzForm(IntegrationTestCase):
	def setUp(self):
		# An event from before Buzz Form had only its other forms moved over.
		self.event = str(BuzzEventFactory.create().name)
		frappe.db.delete("Buzz Form", {"event": self.event, "form_doctype": ["in", REGISTRATION_DOCTYPES]})

	def test_event_without_questions_gets_its_registration_forms(self):
		execute()

		forms = frappe.get_all(
			"Buzz Form",
			filters={"event": self.event, "form_doctype": ["in", REGISTRATION_DOCTYPES]},
			pluck="form_doctype",
		)
		self.assertCountEqual(forms, REGISTRATION_DOCTYPES)

	def test_created_registration_form_keeps_the_event_cutoff(self):
		if not frappe.db.has_column("Buzz Event", "registrations_close_at"):
			self.skipTest("The legacy cutoff column is gone from this site.")
		cutoff = get_datetime(add_days(now_datetime(), 3)).replace(microsecond=0)
		event = frappe.qb.DocType("Buzz Event")
		frappe.qb.update(event).set(event.registrations_close_at, cutoff).where(
			event.name == self.event
		).run()

		execute()

		auto_close_at = frappe.db.get_value(
			"Buzz Form", {"event": self.event, "form_doctype": "Event Booking"}, "auto_close_at"
		)
		self.assertEqual(auto_close_at, cutoff)
