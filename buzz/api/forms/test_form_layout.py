from unittest.mock import patch

import frappe
from frappe.utils import add_days, format_date, get_url, now_datetime

from buzz.api.forms import get_custom_form_data, get_form_builder_fields
from buzz.api.forms.exceptions import InvalidAnswer, UnknownQuestions
from buzz.api.forms.test_custom_forms import FormsTestCase
from buzz.events.og_image import generate, generate_form
from buzz.tests.factories import BuzzEventFactory
from buzz.www.dashboard import form_link_preview


class FeedbackFormCase(FormsTestCase):
	def feedback_form(self, *questions: dict):
		event = BuzzEventFactory.create(team=self.team)
		form = self.form_of(event.name, "Event Feedback")
		for question in questions:
			form.append("questions", {"enabled": 1, **question})
		form.publish = 1
		form.save(ignore_permissions=True)
		return event, form

	def submit_feedback(self, event, answers: dict):
		self.submit(event.route, "feedback", data={"how_can_we_improve": "Fine"}, custom_fields_data=answers)
		return frappe.get_last_doc("Event Feedback", filters={"event": event.name})


class TestFormLayout(FeedbackFormCase):
	def test_layout_rows_get_unique_fieldnames(self):
		_, form = self.feedback_form(
			{"label": "Divider", "fieldtype": "Divider"}, {"label": "Divider", "fieldtype": "Divider"}
		)

		questions = [question.fieldname for question in form.questions if not question.is_standard]
		self.assertEqual(questions, ["divider", "divider_2"])

	def test_layout_rows_take_no_answer(self):
		event, _ = self.feedback_form(
			{"label": "About you", "fieldtype": "Heading"},
			{"label": "Your session", "fieldtype": "Page Break"},
			{"label": "City", "fieldname": "city", "fieldtype": "Data"},
		)

		feedback = self.submit_feedback(event, {"city": "Pune"})
		self.assertEqual([row.fieldname for row in feedback.additional_fields], ["city"])
		with self.assertRaises(UnknownQuestions):
			self.submit_feedback(event, {"about_you": "anything"})

	def test_a_link_answer_must_be_a_web_address(self):
		event, _ = self.feedback_form({"label": "Website", "fieldname": "website", "fieldtype": "URL"})

		self.assertEqual(
			self.submit_feedback(event, {"website": "https://buzz.test"}).additional_fields[0].value,
			"https://buzz.test",
		)
		with self.assertRaises(InvalidAnswer):
			self.submit_feedback(event, {"website": "not a link"})

	def test_a_single_choice_answer_must_be_an_option(self):
		event, _ = self.feedback_form(
			{"label": "Level", "fieldname": "level", "fieldtype": "Radio", "options": "Beginner\nAdvanced"}
		)

		self.assertEqual(
			self.submit_feedback(event, {"level": "Advanced"}).additional_fields[0].value, "Advanced"
		)
		with self.assertRaises(InvalidAnswer):
			self.submit_feedback(event, {"level": "Expert"})

	def test_form_data_carries_description_label_and_width(self):
		event, form = self.feedback_form(
			{"label": "City", "fieldname": "city", "fieldtype": "Data", "width": "Half"}
		)
		form.update({"description": "Tell us how it went", "submit_label": "Send feedback"})
		form.save(ignore_permissions=True)

		data = get_custom_form_data(event.route, "feedback")

		self.assertEqual((data.form_description, data.submit_label), ("Tell us how it went", "Send feedback"))
		self.assertEqual(data.custom_fields[0].width, "Half")


class TestFormBuilderFields(FormsTestCase):
	def test_lists_offered_and_locked_doctype_fields(self):
		event = BuzzEventFactory.create(team=self.team)
		form = self.form_of(event.name, "Sponsorship Enquiry")

		fields = {field.fieldname: field for field in get_form_builder_fields(form.name).fields}

		self.assertTrue(fields["contact_email"].offered and fields["contact_email"].locked)
		self.assertFalse(fields["phone"].locked)
		self.assertTrue(
			all(field.offered for field in fields.values() if field.fieldname in ("tier", "company_name"))
		)


class TestFormLinkPreview(FeedbackFormCase):
	def test_a_form_page_carries_its_preview_text(self):
		event, form = self.feedback_form()
		form.update({"meta_title": "Tell us everything", "meta_description": "Two minutes"})
		form.save(ignore_permissions=True)

		preview = form_link_preview(f"/b/{event.route}/feedback")

		self.assertEqual((preview["title"], preview["description"]), ("Tell us everything", "Two minutes"))

	def test_other_pages_carry_none(self):
		self.assertIsNone(form_link_preview("/b/manage/events"))
		self.assertIsNone(form_link_preview("/b/bookings"))

	def test_uploaded_image_is_shared_as_a_full_address(self):
		event, form = self.feedback_form()
		form.meta_image = "/files/cfp-cover.png"
		form.save(ignore_permissions=True)

		preview = form_link_preview(f"/b/{event.route}/feedback")

		self.assertEqual(preview["image"], get_url("/files/cfp-cover.png"))

	def test_default_description_says_when_the_form_closes(self):
		event, form = self.feedback_form()
		close_at = add_days(now_datetime(), 10)
		form.update({"description": "Tell us how it went.", "auto_close_at": close_at})
		form.save(ignore_permissions=True)

		preview = form_link_preview(f"/b/{event.route}/feedback")

		closes = format_date(close_at, "d MMM")
		self.assertEqual(preview["description"], f"Tell us how it went. Submissions close on {closes}.")

	def test_a_published_form_gets_its_own_share_image(self):
		event, form = self.feedback_form()

		generate_form(form.name)

		og_image = frappe.db.get_value("Buzz Form", form.name, "og_image")
		self.addCleanup(self.delete_files, form.name)
		self.assertTrue(og_image.endswith(".png"))
		self.assertEqual(form_link_preview(f"/b/{event.route}/feedback")["image"], get_url(og_image))

	def test_redrawing_an_event_redraws_its_forms(self):
		event, form = self.feedback_form()

		with patch("frappe.enqueue") as enqueue:
			generate(str(event.name))

		self.addCleanup(self.delete_files, str(event.name))
		self.assertIn(form.name, [call.kwargs.get("form_name") for call in enqueue.call_args_list])

	def delete_files(self, attached_to: str):
		# A rollback leaves the rendered files on disk
		for name in frappe.get_all("File", filters={"attached_to_name": attached_to}, pluck="name"):
			frappe.delete_doc("File", name, ignore_permissions=True, force=True)
