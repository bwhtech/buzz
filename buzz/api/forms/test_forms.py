import frappe
from frappe.tests import IntegrationTestCase

from buzz.api.forms import (
	get_custom_form_data,
	get_dial_codes,
	get_event_proposal_form_data,
	submit_custom_form,
	submit_event_proposal,
)
from buzz.api.forms.exceptions import (
	EventNotFound,
	FormNotAvailable,
	LoginRequired,
	MandatoryFieldsHidden,
	ProposalsNotAccepted,
	SubmissionsClosed,
	UnknownExcludedFields,
)
from buzz.api.forms.fields import (
	STANDARD_EXCLUDE_FIELDS,
	get_form_fields,
	get_link_field_options,
	parse_excluded_fields,
	validate_excluded_fields,
)

# Renderable Talk Proposal fields (after STANDARD_EXCLUDE_FIELDS + auto-set event/submitted_by):
#   title (reqd, Data), description (Text Editor), speakers (reqd, Table), phone (Phone)
TALK_PROPOSAL_EXCLUDE = STANDARD_EXCLUDE_FIELDS | {"event", "submitted_by"}


def ensure_prompt_named_record(doctype, name):
	# Event Category / Event Host use autoname "prompt" -> name set explicitly.
	if frappe.db.exists(doctype, name):
		return name
	doc = frappe.new_doc(doctype)
	doc.name = name
	doc.insert(ignore_permissions=True)
	return doc.name


class FormsTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Test Forms Category")
		cls.host = ensure_prompt_named_record("Event Host", "Test Forms Host")

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()

	def build_event(self, is_published=1, **form_row):
		"""An event carrying one custom form. Returns the inserted event and its form route."""
		event = frappe.new_doc("Buzz Event")
		event.update(
			{
				"title": f"Test Event {frappe.generate_hash(length=6)}",
				"start_date": "2030-01-01",
				"end_date": "2030-01-01",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"category": self.category,
				"host": self.host,
				"is_published": is_published,
			}
		)
		form_row.setdefault("form_doctype", "Talk Proposal")
		form_row.setdefault("route", f"propose-{frappe.generate_hash(length=6)}")
		form_row.setdefault("publish", 1)
		event.set("custom_forms", [])
		event.append("custom_forms", form_row)
		event.insert(ignore_permissions=True)
		event.reload()
		return event, form_row["route"]


class TestParseExcludedFields(IntegrationTestCase):
	def test_blank_returns_none(self):
		self.assertIsNone(parse_excluded_fields(None))
		self.assertIsNone(parse_excluded_fields(""))
		self.assertIsNone(parse_excluded_fields("   "))
		self.assertIsNone(parse_excluded_fields(", ,,"))

	def test_trims_and_drops_empties(self):
		self.assertEqual(parse_excluded_fields("a, b ,,c"), {"a", "b", "c"})

	def test_single_field(self):
		self.assertEqual(parse_excluded_fields("title"), {"title"})


class TestGetFormFields(IntegrationTestCase):
	def test_excluding_a_field_drops_it(self):
		exclude_fields = TALK_PROPOSAL_EXCLUDE | {"phone"}
		fields = get_form_fields("Talk Proposal", exclude_fields)
		returned = {f["fieldname"] for f in fields}
		self.assertNotIn("phone", returned)
		self.assertTrue({"title", "description", "speakers"} <= returned)

	def test_no_extra_exclude_returns_all_renderable(self):
		fields = get_form_fields("Talk Proposal", TALK_PROPOSAL_EXCLUDE)
		returned = {f["fieldname"] for f in fields}
		self.assertTrue({"title", "description", "speakers", "phone"} <= returned)

	def test_layout_breaks_pass_through(self):
		# With layout breaks on, section/column breaks are emitted even when other fields are excluded.
		exclude_fields = TALK_PROPOSAL_EXCLUDE | {"description", "speakers", "phone"}
		fields = get_form_fields("Talk Proposal", exclude_fields, with_layout_breaks=True)
		real_fields = {
			f["fieldname"] for f in fields if f["fieldtype"] not in ("Section Break", "Column Break")
		}
		breaks = [f for f in fields if f["fieldtype"] in ("Section Break", "Column Break")]
		self.assertIn("title", real_fields)
		self.assertFalse({"description", "speakers", "phone"} & real_fields)
		self.assertTrue(breaks, "expected layout breaks to pass through")

	def test_table_field_carries_child_fields(self):
		speakers = next(
			f for f in get_form_fields("Talk Proposal", TALK_PROPOSAL_EXCLUDE) if f["fieldname"] == "speakers"
		)
		child_fieldnames = {f["fieldname"] for f in speakers["child_fields"]}
		self.assertTrue({"first_name", "email"} <= child_fieldnames)


class TestGetLinkFieldOptions(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Test Forms Category")
		cls.host = ensure_prompt_named_record("Event Host", "Test Forms Host")

	def make_tier(self, title="Gold Tier"):
		event = frappe.new_doc("Buzz Event")
		event.update(
			{
				"title": f"Test Event {frappe.generate_hash(length=6)}",
				"start_date": "2030-01-01",
				"end_date": "2030-01-01",
				"start_time": "10:00:00",
				"end_time": "18:00:00",
				"medium": "Online",
				"category": self.category,
				"host": self.host,
			}
		)
		event.insert(ignore_permissions=True)
		tier = frappe.new_doc("Sponsorship Tier")
		tier.update({"event": event.name, "title": title, "price": 1000, "currency": "INR"})
		tier.insert(ignore_permissions=True)
		return tier

	def test_options_have_value_label_shape(self):
		options = get_link_field_options("Event Host")
		self.assertTrue(options)
		self.assertTrue(all(set(option) == {"value", "label"} for option in options))

	def test_no_title_field_label_falls_back_to_name(self):
		# Event Host has no title field -> label mirrors the name.
		match = next(o for o in get_link_field_options("Event Host") if o["value"] == self.host)
		self.assertEqual(match["label"], self.host)

	def test_title_field_used_as_label(self):
		# Sponsorship Tier names are hashes; its title field is the readable label.
		tier = self.make_tier(title="Gold Tier")
		match = next(o for o in get_link_field_options("Sponsorship Tier") if o["value"] == tier.name)
		self.assertEqual(match["label"], "Gold Tier")
		self.assertNotEqual(match["value"], match["label"])

	def test_null_title_falls_back_to_name(self):
		tier = self.make_tier()
		# Blank the title directly (bypasses the reqd validation) to exercise the fallback.
		frappe.db.set_value("Sponsorship Tier", tier.name, "title", "")
		match = next(o for o in get_link_field_options("Sponsorship Tier") if o["value"] == tier.name)
		self.assertEqual(match["label"], tier.name)


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
		self.assertEqual(data.success_title, "Nice one")
		self.assertEqual(data.success_message, "See you there")
		self.assertEqual(data.form_title, "Talk Proposal")


class TestCustomFormExcludedFields(FormsTestCase):
	def test_get_custom_form_data_hides_excluded_fields(self):
		event, form_route = self.build_event(excluded_fields="phone")
		data = get_custom_form_data(event.route, form_route)
		returned = {f["fieldname"] for f in data.form_fields}
		self.assertNotIn("phone", returned)
		self.assertTrue({"title", "description", "speakers"} <= returned)

	def test_get_custom_form_data_empty_excluded_fields_returns_all(self):
		event, form_route = self.build_event(excluded_fields="")
		data = get_custom_form_data(event.route, form_route)
		returned = {f["fieldname"] for f in data.form_fields}
		self.assertTrue({"title", "description", "speakers", "phone"} <= returned)

	def test_submit_drops_excluded_field_value(self):
		# phone is excluded -> a posted phone value must be dropped.
		event, form_route = self.build_event(excluded_fields="phone")
		submit_custom_form(
			event.route,
			form_route,
			data={
				"title": "Hidden Phone Test",
				"description": "<p>desc</p>",
				"speakers": [{"first_name": "Jane", "email": "jane@example.com"}],
				"phone": "+919999999999",
			},
		)
		created = frappe.get_last_doc("Talk Proposal", filters={"title": "Hidden Phone Test"})
		self.assertEqual(str(created.event), str(event.name))
		self.assertFalse(created.phone, f"phone should be dropped but was {created.phone!r}")
		# Non-excluded fields (and child rows) must still be written.
		self.assertEqual(created.title, "Hidden Phone Test")
		self.assertEqual(created.description, "<p>desc</p>")
		self.assertEqual(len(created.speakers), 1)
		self.assertEqual(created.speakers[0].first_name, "Jane")
		self.assertEqual(created.speakers[0].email, "jane@example.com")


class TestCustomFormAccess(FormsTestCase):
	def test_status_codes(self):
		self.assertEqual(EventNotFound.http_status_code, 404)
		self.assertEqual(FormNotAvailable.http_status_code, 404)
		self.assertEqual(LoginRequired.http_status_code, 401)
		self.assertEqual(SubmissionsClosed.http_status_code, 409)

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
		frappe.set_user("Guest")
		with self.assertRaises(LoginRequired):
			get_custom_form_data(event.route, form_route)

		self.assertEqual(frappe.local.message_log[-1]["title"], "Login Required")

	def test_guest_cannot_submit_a_login_only_form(self):
		event, form_route = self.build_event(login_required=1)
		frappe.set_user("Guest")
		with self.assertRaises(LoginRequired):
			submit_custom_form(event.route, form_route, data={"title": "Nope"})

	def test_logged_in_user_passes_the_login_gate(self):
		event, form_route = self.build_event(login_required=1)
		self.assertFalse(get_custom_form_data(event.route, form_route).closed)


class TestCustomFormClosing(FormsTestCase):
	def test_closed_form_returns_the_closed_copy_and_no_fields(self):
		event, form_route = self.build_event(
			auto_close_at="2020-01-01 00:00:00",
			closed_title="All done",
			closed_message="Come back next year",
		)
		data = get_custom_form_data(event.route, form_route)
		self.assertTrue(data.closed)
		self.assertEqual(data.form_fields, [])
		self.assertEqual(data.custom_fields, [])
		self.assertEqual(data.closed_title, "All done")
		self.assertEqual(data.closed_message, "Come back next year")
		self.assertEqual(data.success_title, "")
		self.assertEqual(data.success_message, "")

	def test_future_close_time_leaves_the_form_open(self):
		event, form_route = self.build_event(auto_close_at="2099-01-01 00:00:00")
		self.assertFalse(get_custom_form_data(event.route, form_route).closed)

	def test_submitting_a_closed_form_conflicts(self):
		event, form_route = self.build_event(auto_close_at="2020-01-01 00:00:00")
		with self.assertRaises(SubmissionsClosed):
			submit_custom_form(event.route, form_route, data={"title": "Too late"})

		self.assertEqual(frappe.local.message_log[-1]["title"], "Submissions Closed")


class TestCustomFormCustomFields(FormsTestCase):
	def build_event_with_custom_field(self, **field):
		event, form_route = self.build_event()
		field.setdefault("label", "Dietary Preference")
		field.setdefault("fieldtype", "Data")
		frappe.get_doc(
			{
				"doctype": "Buzz Custom Field",
				"event": event.name,
				"applied_to": "Custom Form",
				"custom_form_doctype": "Talk Proposal",
				"enabled": 1,
				**field,
			}
		).insert(ignore_permissions=True)
		frappe.clear_document_cache("Buzz Event", event.name)
		return event, form_route

	def test_definitions_are_returned_with_the_form(self):
		event, form_route = self.build_event_with_custom_field(mandatory=1, order=2, placeholder="Veg?")
		custom_fields = get_custom_form_data(event.route, form_route).custom_fields
		self.assertEqual(len(custom_fields), 1)
		self.assertEqual(custom_fields[0].label, "Dietary Preference")
		# Check fields travel as 0/1, not booleans.
		self.assertEqual(custom_fields[0].mandatory, 1)
		self.assertEqual(custom_fields[0].order, 2)

	def test_submitted_values_land_in_additional_fields(self):
		event, form_route = self.build_event_with_custom_field()
		submit_custom_form(
			event.route,
			form_route,
			data={
				"title": "Custom Field Test",
				"speakers": [{"first_name": "Jane", "email": "jane@example.com"}],
			},
			custom_fields_data={"dietary_preference": "Vegetarian", "not_a_custom_field": "dropped"},
		)
		created = frappe.get_last_doc("Talk Proposal", filters={"title": "Custom Field Test"})
		self.assertEqual(len(created.additional_fields), 1)
		self.assertEqual(created.additional_fields[0].fieldname, "dietary_preference")
		self.assertEqual(created.additional_fields[0].value, "Vegetarian")

	def test_blank_values_are_not_appended(self):
		event, form_route = self.build_event_with_custom_field()
		submit_custom_form(
			event.route,
			form_route,
			data={
				"title": "Blank Custom Field Test",
				"speakers": [{"first_name": "Jane", "email": "jane@example.com"}],
			},
			custom_fields_data={"dietary_preference": ""},
		)
		created = frappe.get_last_doc("Talk Proposal", filters={"title": "Blank Custom Field Test"})
		self.assertEqual(created.additional_fields, [])


class TestCustomFormLinkEventFilter(FormsTestCase):
	def make_sponsorship_event(self):
		return self.build_event(
			form_doctype="Sponsorship Enquiry", route=f"sponsor-{frappe.generate_hash(length=6)}"
		)

	def make_tier(self, event_name, title):
		tier = frappe.new_doc("Sponsorship Tier")
		tier.update({"event": event_name, "title": title, "price": 100, "currency": "INR"})
		tier.insert(ignore_permissions=True)
		return tier.name

	def test_tier_options_filtered_to_form_event(self):
		event_a, route_a = self.make_sponsorship_event()
		event_b, _ = self.make_sponsorship_event()
		tier_a = self.make_tier(event_a.name, "Gold A")
		tier_b = self.make_tier(event_b.name, "Gold B")

		data = get_custom_form_data(event_a.route, route_a)
		tier_field = next(f for f in data.form_fields if f["fieldname"] == "tier")

		option_values = [option["value"] for option in tier_field["link_options"]]
		self.assertIn(tier_a, option_values)
		self.assertNotIn(tier_b, option_values, "tiers from other events must not leak")

	def test_link_field_without_event_is_not_filtered(self):
		# Country has no `event` field -> it must keep returning the full list.
		event_a, route_a = self.make_sponsorship_event()
		data = get_custom_form_data(event_a.route, route_a)
		country_field = next(f for f in data.form_fields if f["fieldname"] == "country")
		self.assertTrue(len(country_field["link_options"]) > 1)


class TestValidateExcludedFields(IntegrationTestCase):
	def test_status_codes(self):
		self.assertEqual(UnknownExcludedFields.http_status_code, 400)
		self.assertEqual(MandatoryFieldsHidden.http_status_code, 400)

	def test_hiding_mandatory_field_throws(self):
		# speakers is mandatory; it cannot be hidden.
		with self.assertRaises(MandatoryFieldsHidden):
			validate_excluded_fields("Talk Proposal", "speakers")

		self.assertIn("speakers", frappe.local.message_log[-1]["message"])

	def test_unknown_field_throws(self):
		with self.assertRaises(UnknownExcludedFields):
			validate_excluded_fields("Talk Proposal", "phone, not_a_field")

		self.assertIn("not_a_field", frappe.local.message_log[-1]["message"])

	def test_hiding_optional_field_passes(self):
		# phone is optional -> safe to hide.
		validate_excluded_fields("Talk Proposal", "phone")

	def test_system_field_is_noop(self):
		# Auto-set/system fields are never rendered; listing them is a harmless no-op.
		validate_excluded_fields("Talk Proposal", "event, submitted_by")

	def test_blank_is_noop(self):
		validate_excluded_fields("Talk Proposal", "")
		validate_excluded_fields("Talk Proposal", None)


class TestBuzzEventSaveValidatesExcludedFields(FormsTestCase):
	def test_save_hiding_mandatory_throws(self):
		with self.assertRaises(MandatoryFieldsHidden):
			self.build_event(excluded_fields="speakers")

	def test_save_with_unknown_field_throws(self):
		with self.assertRaises(UnknownExcludedFields):
			self.build_event(excluded_fields="phone, bogus_field")

	def test_save_hiding_optional_field_succeeds(self):
		event, _ = self.build_event(excluded_fields="phone")
		self.assertTrue(frappe.db.exists("Buzz Event", event.name))


class TestEventProposalForm(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.category = ensure_prompt_named_record("Event Category", "Test Forms Category")

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.clear_messages()
		self.set_settings(accept_event_proposals=1, allow_guest_event_proposals=1)

	def proposal_payload(self, **overrides):
		return {
			"title": f"Proposal {frappe.generate_hash(length=6)}",
			"category": self.category,
			"start_date": "2030-01-01",
			"start_time": "10:00:00",
			"end_time": "18:00:00",
			"about": "A proposal raised by the forms test suite.",
			**overrides,
		}

	def set_settings(self, **values):
		for fieldname, value in values.items():
			frappe.db.set_single_value("Buzz Settings", fieldname, value)
		frappe.clear_document_cache("Buzz Settings", "Buzz Settings")

	def test_form_data_shape(self):
		self.set_settings(event_proposal_banner_title="Pitch us", event_proposal_success_title="Got it")
		data = get_event_proposal_form_data()
		self.assertEqual(data.banner_title, "Pitch us")
		self.assertEqual(data.success_title, "Got it")
		self.assertTrue(data.form_fields)
		self.assertNotIn("status", {f["fieldname"] for f in data.form_fields})

	def test_disabled_proposals_are_not_found(self):
		self.set_settings(accept_event_proposals=0)
		with self.assertRaises(ProposalsNotAccepted):
			get_event_proposal_form_data()

		self.assertIn("not being accepted", frappe.local.message_log[-1]["message"])

	def test_guest_blocked_when_guest_proposals_are_off(self):
		self.set_settings(allow_guest_event_proposals=0)
		frappe.set_user("Guest")
		with self.assertRaises(LoginRequired):
			get_event_proposal_form_data()

	def test_submit_drops_fields_outside_the_form(self):
		payload = self.proposal_payload(status="Approved")
		submit_event_proposal(data=payload)
		created = frappe.get_last_doc("Event Proposal", filters={"title": payload["title"]})
		# status is excluded, so a posted value must not stick.
		self.assertNotEqual(created.status, "Approved")
		self.assertEqual(created.about, payload["about"])

	def test_guest_can_submit(self):
		payload = self.proposal_payload()
		frappe.set_user("Guest")
		submit_event_proposal(data=payload)
		frappe.set_user("Administrator")
		# Event Proposal has no submitted_by field, so the proposer is only the doc owner.
		created = frappe.get_last_doc("Event Proposal", filters={"title": payload["title"]})
		self.assertEqual(created.owner, "Guest")

	def test_submit_blocked_when_proposals_are_closed(self):
		self.set_settings(accept_event_proposals=0)
		with self.assertRaises(ProposalsNotAccepted):
			submit_event_proposal(data=self.proposal_payload())


class TestDialCodes(IntegrationTestCase):
	def test_shape_and_uniqueness(self):
		codes = get_dial_codes()
		self.assertTrue(codes)
		self.assertTrue(all(set(entry) == {"country", "code", "dial_code"} for entry in codes))
		dial_codes = [entry["dial_code"] for entry in codes]
		self.assertEqual(len(dial_codes), len(set(dial_codes)), "dial codes must be de-duplicated")
		self.assertIn("+91", dial_codes)
