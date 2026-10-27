import frappe

from buzz.api.forms import get_custom_form_data, get_form_builder_fields
from buzz.api.forms.exceptions import InvalidAnswer, UnknownQuestions
from buzz.api.forms.test_custom_forms import FormsTestCase
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
