import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, now_datetime

from buzz.api.forms import get_custom_form_data, submit_custom_form
from buzz.api.forms.exceptions import (
	EventNotFound,
	FormNotAvailable,
	LoginRequired,
	MandatoryFieldsHidden,
	SubmissionsClosed,
	UnknownExcludedFields,
)
from buzz.tests.factories import (
	BuzzCustomFieldFactory,
	BuzzEventFactory,
	BuzzTeamFactory,
	EventCategoryFactory,
	EventHostFactory,
	SponsorshipTierFactory,
)

SPEAKERS = [{"first_name": "Jane", "email": "jane@example.com"}]


class FormsTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.team = BuzzTeamFactory.create_owned_by().name
		cls.category = EventCategoryFactory.create().name
		cls.host = EventHostFactory.create(team=cls.team).name

	def setUp(self):
		frappe.clear_messages()

	def build_event(self, **form_row):
		"""An event carrying one custom form. Returns the inserted event and its form route."""
		form_row = {
			"form_doctype": "Talk Proposal",
			"route": f"propose-{frappe.generate_hash(length=6)}",
			"publish": 1,
			**form_row,
		}
		event = BuzzEventFactory.create(
			team=self.team, category=self.category, host=self.host, custom_forms=[form_row]
		)
		event.reload()
		return event, form_row["route"]

	def submitted_proposal(self, title: str):
		return frappe.get_last_doc("Talk Proposal", filters={"title": title})


class TestCustomFormResponse(FormsTestCase):
	def test_event_name_travels_as_a_string(self):
		event, form_route = self.build_event()

		data = get_custom_form_data(event.route, form_route)

		self.assertEqual(data.event.name, str(event.name))
		self.assertIsInstance(data.__json__()["event"]["name"], str)

	def test_open_form_carries_success_copy(self):
		event, form_route = self.build_event(success_title="Nice one", success_message="See you there")

		data = get_custom_form_data(event.route, form_route)

		self.assertFalse(data.closed)
		self.assertEqual((data.success_title, data.success_message), ("Nice one", "See you there"))
		self.assertEqual(data.form_title, "Talk Proposal")


class TestCustomFormExcludedFields(FormsTestCase):
	def test_get_custom_form_data_hides_excluded_fields(self):
		returned = self.returned_fields(excluded_fields="phone")

		self.assertNotIn("phone", returned)
		self.assertTrue({"title", "description", "speakers"} <= returned)

	def test_get_custom_form_data_empty_excluded_fields_returns_all(self):
		self.assertTrue(
			{"title", "description", "speakers", "phone"} <= self.returned_fields(excluded_fields="")
		)

	def test_submit_drops_excluded_field_value(self):
		event, form_route = self.build_event(excluded_fields="phone")
		data = {"title": "Hidden Phone", "description": "<p>desc</p>", "speakers": SPEAKERS}

		submit_custom_form(event.route, form_route, data={**data, "phone": "+919999999999"})

		created = self.submitted_proposal("Hidden Phone")
		self.assertEqual(str(created.event), str(event.name))
		self.assertFalse(created.phone, f"phone should be dropped but was {created.phone!r}")
		# Non-excluded fields (and child rows) must still be written.
		self.assertEqual(created.description, "<p>desc</p>")
		self.assertEqual(
			[(row.first_name, row.email) for row in created.speakers], [("Jane", "jane@example.com")]
		)

	def test_save_hiding_mandatory_throws(self):
		with self.assertRaises(MandatoryFieldsHidden):
			self.build_event(excluded_fields="speakers")

	def test_save_with_unknown_field_throws(self):
		with self.assertRaises(UnknownExcludedFields):
			self.build_event(excluded_fields="phone, bogus_field")

	def test_save_hiding_optional_field_succeeds(self):
		event, _ = self.build_event(excluded_fields="phone")

		self.assertTrue(frappe.db.exists("Buzz Event", event.name))

	def returned_fields(self, **form_row) -> set[str]:
		event, form_route = self.build_event(**form_row)
		return {f["fieldname"] for f in get_custom_form_data(event.route, form_route).form_fields}


class TestCustomFormAccess(FormsTestCase):
	def test_unknown_event_route(self):
		with self.assertRaises(EventNotFound):
			get_custom_form_data("no-such-event-route", "feedback")

		self.assertEqual(frappe.local.message_log[-1]["title"], "Not Found")
		self.assertIn("Event not found", frappe.local.message_log[-1]["message"])

	def test_unpublished_event_is_not_found(self):
		# A route is only assigned on publish, so unpublish after the fact to keep one.
		event, form_route = self.build_event()
		frappe.db.set_value("Buzz Event", event.name, "is_published", 0)
		frappe.clear_document_cache("Buzz Event", event.name)

		with self.assertRaises(EventNotFound):
			get_custom_form_data(event.route, form_route)

	def test_unknown_form_route(self):
		event, _ = self.build_event()

		with self.assertRaises(FormNotAvailable):
			get_custom_form_data(event.route, "no-such-form-route")

		self.assertIn("not available for this event", frappe.local.message_log[-1]["message"])

	def test_unpublished_form_row_is_not_available(self):
		event, form_route = self.build_event(publish=0)

		with self.assertRaises(FormNotAvailable):
			get_custom_form_data(event.route, form_route)

	def test_guest_needs_login_when_form_requires_it(self):
		event, form_route = self.build_event(login_required=1)

		with self.set_user("Guest"), self.assertRaises(LoginRequired):
			get_custom_form_data(event.route, form_route)

		self.assertEqual(frappe.local.message_log[-1]["title"], "Login Required")

	def test_guest_cannot_submit_a_login_only_form(self):
		event, form_route = self.build_event(login_required=1)

		with self.set_user("Guest"), self.assertRaises(LoginRequired):
			submit_custom_form(event.route, form_route, data={"title": "Nope"})

	def test_logged_in_user_passes_the_login_gate(self):
		event, form_route = self.build_event(login_required=1)

		self.assertFalse(get_custom_form_data(event.route, form_route).closed)


class TestCustomFormClosing(FormsTestCase):
	def test_closed_form_returns_the_closed_copy_and_no_fields(self):
		event, form_route = self.build_event(
			auto_close_at=add_to_date(now_datetime(), days=-1),
			closed_title="All done",
			closed_message="Come back next year",
		)

		data = get_custom_form_data(event.route, form_route)

		self.assertTrue(data.closed)
		self.assertEqual((data.form_fields, data.custom_fields), ([], []))
		self.assertEqual((data.closed_title, data.closed_message), ("All done", "Come back next year"))
		self.assertEqual((data.success_title, data.success_message), ("", ""))

	def test_future_close_time_leaves_the_form_open(self):
		event, form_route = self.build_event(auto_close_at=add_to_date(now_datetime(), days=30))

		self.assertFalse(get_custom_form_data(event.route, form_route).closed)

	def test_submitting_a_closed_form_conflicts(self):
		event, form_route = self.build_event(auto_close_at=add_to_date(now_datetime(), days=-1))

		with self.assertRaises(SubmissionsClosed):
			submit_custom_form(event.route, form_route, data={"title": "Too late"})

		self.assertEqual(frappe.local.message_log[-1]["title"], "Submissions Closed")


class TestCustomFormCustomFields(FormsTestCase):
	def test_definitions_are_returned_with_the_form(self):
		event, form_route = self.build_event_with_custom_field(mandatory=1, order=2, placeholder="Veg?")

		custom_fields = get_custom_form_data(event.route, form_route).custom_fields

		self.assertEqual([field.label for field in custom_fields], ["Dietary Preference"])
		# Check fields travel as 0/1, not booleans.
		self.assertEqual((custom_fields[0].mandatory, custom_fields[0].order), (1, 2))

	def test_submitted_values_land_in_additional_fields(self):
		created = self.submit_with_custom_fields(
			"Custom Field", {"dietary_preference": "Vegetarian", "not_a_custom_field": "dropped"}
		)

		values = [(row.fieldname, row.value) for row in created.additional_fields]
		self.assertEqual(values, [("dietary_preference", "Vegetarian")])

	def test_blank_values_are_not_appended(self):
		created = self.submit_with_custom_fields("Blank Custom Field", {"dietary_preference": ""})

		self.assertEqual(created.additional_fields, [])

	def build_event_with_custom_field(self, **field):
		event, form_route = self.build_event()
		BuzzCustomFieldFactory.create(
			event=event.name,
			applied_to="Custom Form",
			custom_form_doctype="Talk Proposal",
			label="Dietary Preference",
			fieldtype="Data",
			**field,
		)
		frappe.clear_document_cache("Buzz Event", event.name)
		return event, form_route

	def submit_with_custom_fields(self, title: str, custom_fields_data: dict):
		event, form_route = self.build_event_with_custom_field()
		data = {"title": title, "speakers": SPEAKERS}
		submit_custom_form(event.route, form_route, data=data, custom_fields_data=custom_fields_data)
		return self.submitted_proposal(title)


class TestCustomFormLinkEventFilter(FormsTestCase):
	def test_tier_options_filtered_to_form_event(self):
		event, form_route = self.build_sponsorship_event()
		other_event, _ = self.build_sponsorship_event()
		tier = SponsorshipTierFactory.create(event=event.name, title="Gold A").name
		other_tier = SponsorshipTierFactory.create(event=other_event.name, title="Gold B").name

		option_values = [option["value"] for option in self.link_options(event, form_route, "tier")]

		self.assertIn(tier, option_values)
		self.assertNotIn(other_tier, option_values, "tiers from other events must not leak")

	def test_link_field_without_event_is_not_filtered(self):
		# Country has no `event` field -> it must keep returning the full list.
		event, form_route = self.build_sponsorship_event()

		self.assertTrue(len(self.link_options(event, form_route, "country")) > 1)

	def build_sponsorship_event(self):
		event, _ = self.build_event()
		form = frappe.get_doc("Sponsor Enquiry Form", {"event": event.name})
		form.publish = 1
		form.save()
		return event, form.route

	def link_options(self, event, form_route: str, fieldname: str) -> list[dict]:
		fields = get_custom_form_data(event.route, form_route).form_fields
		return next(f for f in fields if f["fieldname"] == fieldname)["link_options"]
