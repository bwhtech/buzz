import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.events import archive_event
from buzz.api.events.exceptions import CannotManageEvent
from buzz.tests.factories import BuzzEventFactory, BuzzFormFactory, BuzzTeamFactory, UserFactory


class TestArchiveEvent(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.owner = UserFactory.create_once("archive-owner@example.com").name
		cls.outsider = UserFactory.create_once("archive-outsider@example.com").name
		cls.team = BuzzTeamFactory.create_owned_by(cls.owner).name

	def test_archiving_unpublishes_the_event_and_closes_its_forms(self):
		event = self.create_event(is_published=1)
		publish_forms(event)

		self.archive_as(self.owner, event)

		doc = frappe.get_doc("Buzz Event", event)
		self.assertFalse(doc.is_published)
		self.assertTrue(all(form.is_closed for form in event_forms(event)))

	def test_archiving_closes_registrations(self):
		"""The booking gates stop at `is_published`, but the cutoff has to agree with them."""
		event = self.create_event(is_published=1)
		BuzzFormFactory.set_registration_cutoff(event, None)

		self.archive_as(self.owner, event)

		form = frappe.get_doc("Buzz Form", {"event": event, "form_doctype": "Event Booking"})
		self.assertTrue(form.publish)
		self.assertIsNotNone(form.auto_close_at)

	def test_archiving_an_archived_event_is_a_no_op(self):
		"""validate() runs on the way through, so a second archive must not throw."""
		event = self.create_event("unpublished")

		self.archive_as(self.owner, event)

		self.assertFalse(frappe.db.get_value("Buzz Event", event, "is_published"))

	def test_someone_outside_the_team_cannot_archive(self):
		event = self.create_event(is_published=1)

		with self.assertRaises(CannotManageEvent):
			self.archive_as(self.outsider, event)

		self.assertTrue(frappe.db.get_value("Buzz Event", event, "is_published"))

	def create_event(self, *traits: str, **overrides) -> str:
		return str(BuzzEventFactory.create(*traits, team=self.team, **overrides).name)

	def archive_as(self, user: str, event: str):
		with self.set_user(user):
			archive_event(event)


def publish_forms(event: str):
	"""`publish` defaults to 0, so the forms have to be opened before a close means anything."""
	for name in frappe.get_all("Buzz Form", {"event": event}, pluck="name"):
		frappe.db.set_value("Buzz Form", name, "publish", 1)


def event_forms(event: str) -> list:
	return [
		frappe.get_doc("Buzz Form", name)
		for name in frappe.get_all("Buzz Form", {"event": event}, pluck="name")
	]
