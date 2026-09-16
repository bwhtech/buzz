import frappe
from frappe.tests import IntegrationTestCase

from buzz.events.doctype.buzz_team.test_buzz_team import create_owned_team
from buzz.patches.migrate_sponsor_enquiry_forms import SponsorFormMigration


class SponsorFormMigrationTestCase(IntegrationTestCase):
	@staticmethod
	def ensure_category():
		name = "Sponsor Migration Test Category"
		if not frappe.db.exists("Event Category", name):
			frappe.get_doc({"doctype": "Event Category", "name": name}).insert(ignore_permissions=True)
		return name

	@staticmethod
	def ensure_host():
		name = "Sponsor Migration Test Host"
		host = frappe.db.get_value("Event Host", {"host_name": name})
		if not host:
			host = (
				frappe.get_doc({"doctype": "Event Host", "host_name": name})
				.insert(ignore_permissions=True)
				.name
			)
		return host

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()
		self.category = self.ensure_category()
		self.host = self.ensure_host()
		self.team = create_owned_team(f"Sponsor Migration {frappe.generate_hash(length=6)}", "Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def make_legacy_event(self):
		event = frappe.get_doc(
			{
				"doctype": "Buzz Event",
				"title": f"Sponsor Migration {frappe.generate_hash(length=6)}",
				"start_date": "2030-01-01",
				"end_date": "2030-01-01",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"category": self.category,
				"host": self.host,
				"team": self.team,
				"is_published": 1,
			}
		).insert(ignore_permissions=True)
		form = frappe.get_doc("Sponsor Enquiry Form", {"event": event.name})
		frappe.delete_doc("Sponsor Enquiry Form", form.name, force=1)
		frappe.clear_document_cache("Buzz Event", event.name)
		return event

	def add_legacy_form(self, event, **values):
		row = frappe.get_doc(
			{
				"doctype": "Buzz Event Form",
				"parent": event.name,
				"parenttype": "Buzz Event",
				"parentfield": "custom_forms",
				"form_doctype": "Sponsorship Enquiry",
				"route": "legacy-sponsor",
				"publish": 1,
				"login_required": 1,
				**values,
			}
		)
		row.db_insert()
		return row

	def add_legacy_question(self, event, **values):
		question = frappe.get_doc(
			{
				"doctype": "Buzz Custom Field",
				"event": event.name,
				"applied_to": "Custom Form",
				"custom_form_doctype": "Sponsorship Enquiry",
				"enabled": 1,
				"label": "Legacy budget",
				"fieldname": "legacy_budget",
				"fieldtype": "Number",
				"order": 1,
				**values,
			}
		)
		question.db_insert()
		return question


class TestMigrateSponsorEnquiryForms(SponsorFormMigrationTestCase):
	def test_migrates_settings_questions_and_preserves_existing_enquiries(self):
		event = self.make_legacy_event()
		legacy = self.add_legacy_form(
			event,
			login_required=0,
			route="apply-sponsor",
			success_title="Received",
			success_message="We will reply soon.",
			closed_title="Closed",
			closed_message="Try next year.",
			auto_close_at="2031-01-01 00:00:00",
			excluded_fields="website",
		)
		question = self.add_legacy_question(event, mandatory=1, options="unused", order=2)
		disabled = self.add_legacy_question(
			event, label="Disabled", fieldname="disabled_question", enabled=0, order=1
		)
		tier = frappe.get_doc(
			{
				"doctype": "Sponsorship Tier",
				"event": event.name,
				"title": "Legacy tier",
				"price": 100,
				"currency": "INR",
			}
		).insert(ignore_permissions=True)
		enquiry = frappe.get_doc(
			{
				"doctype": "Sponsorship Enquiry",
				"event": event.name,
				"company_name": "Existing Sponsor",
				"company_logo": "/files/acme.png",
				"tier": tier.name,
				"status": "Withdrawn",
				"additional_fields": [{"fieldname": "legacy_budget", "label": "Legacy budget", "value": "0"}],
			}
		).insert(ignore_permissions=True)
		legacy_form_count = frappe.db.count("Buzz Event Form", {"parent": event.name})

		SponsorFormMigration().run()
		form = frappe.get_doc("Sponsor Enquiry Form", {"event": event.name})
		enquiry.reload()

		self.assertEqual(form.route, "apply-sponsor")
		self.assertTrue(form.allow_guest_submissions)
		self.assertEqual(form.success_title, "Received")
		self.assertEqual(form.success_message, "We will reply soon.")
		self.assertEqual(form.closed_title, "Closed")
		self.assertEqual(form.closed_message, "Try next year.")
		self.assertEqual(str(form.auto_close_at), "2031-01-01 00:00:00")
		self.assertEqual(form.excluded_fields, "website")
		self.assertEqual(
			[row.fieldname for row in form.custom_fields], ["disabled_question", "legacy_budget"]
		)
		self.assertFalse(form.custom_fields[0].enabled)
		self.assertTrue(form.custom_fields[1].mandatory)
		self.assertFalse(frappe.db.exists("Buzz Event Form", legacy.name))
		self.assertFalse(frappe.db.get_value("Buzz Custom Field", question.name, "enabled"))
		self.assertFalse(frappe.db.get_value("Buzz Custom Field", disabled.name, "enabled"))
		self.assertEqual(frappe.db.count("Buzz Event Form", {"parent": event.name}), legacy_form_count - 1)
		self.assertFalse(enquiry.enquiry_form)
		self.assertEqual(enquiry.tier, tier.name)
		self.assertEqual(enquiry.status, "Withdrawn")
		self.assertEqual(enquiry.additional_fields[0].value, "0")

	def test_missing_legacy_form_creates_a_closed_login_only_default(self):
		event = self.make_legacy_event()

		SponsorFormMigration().run()
		form = frappe.get_doc("Sponsor Enquiry Form", {"event": event.name})

		self.assertEqual(form.route, "enquire-sponsorship")
		self.assertFalse(form.publish)
		self.assertFalse(form.allow_guest_submissions)

	def test_second_run_is_idempotent(self):
		event = self.make_legacy_event()
		self.add_legacy_form(event)
		self.add_legacy_question(event)

		migration = SponsorFormMigration()
		migration.run()
		form_name = frappe.db.get_value("Sponsor Enquiry Form", {"event": event.name})
		migration.run()

		self.assertEqual(frappe.db.count("Sponsor Enquiry Form", {"event": event.name}), 1)
		self.assertEqual(frappe.db.get_value("Sponsor Enquiry Form", {"event": event.name}), form_name)
		self.assertFalse(
			frappe.db.exists("Buzz Event Form", {"parent": event.name, "form_doctype": "Sponsorship Enquiry"})
		)

	def test_conflicts_are_reported_before_any_event_is_changed(self):
		migratable = self.make_legacy_event()
		legacy = self.add_legacy_form(migratable)
		conflicted = self.make_legacy_event()
		self.add_legacy_form(conflicted, route="first")
		self.add_legacy_form(conflicted, route="second")

		with self.assertRaises(frappe.ValidationError):
			SponsorFormMigration().run()

		self.assertFalse(frappe.db.exists("Sponsor Enquiry Form", {"event": migratable.name}))
		self.assertTrue(frappe.db.exists("Buzz Event Form", legacy.name))

	def test_invalid_question_keys_preflight_before_any_event_is_changed(self):
		migratable = self.make_legacy_event()
		legacy = self.add_legacy_form(migratable)
		conflicted = self.make_legacy_event()
		self.add_legacy_question(conflicted, fieldname="duplicate")
		self.add_legacy_question(conflicted, label="Duplicate", fieldname="duplicate")

		with self.assertRaises(frappe.ValidationError):
			SponsorFormMigration().run()

		self.assertFalse(frappe.db.exists("Sponsor Enquiry Form", {"event": migratable.name}))
		self.assertTrue(frappe.db.exists("Buzz Event Form", legacy.name))

	def test_route_collision_preflight_before_any_event_is_changed(self):
		migratable = self.make_legacy_event()
		legacy = self.add_legacy_form(migratable)
		conflicted = self.make_legacy_event()
		self.add_legacy_form(conflicted, route="feedback")

		with self.assertRaises(frappe.ValidationError):
			SponsorFormMigration().run()

		self.assertFalse(frappe.db.exists("Sponsor Enquiry Form", {"event": migratable.name}))
		self.assertTrue(frappe.db.exists("Buzz Event Form", legacy.name))
