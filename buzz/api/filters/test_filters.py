import json

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from buzz.api.filters.conditions import ListConditions, filter_field, question_fields
from buzz.api.filters.exceptions import InvalidFilter
from buzz.tests.factories import BuzzEventFactory, SponsorshipEnquiryFactory

QUESTIONS = [
	frappe._dict(fieldname="booth", label="Needs a booth", fieldtype="Check"),
	frappe._dict(fieldname="size", label="Company size", fieldtype="Select", options="11-50\n200+"),
	frappe._dict(
		fieldname="interests", label="Interested in", fieldtype="Multi Select", options="Talk\nSwag"
	),
	frappe._dict(fieldname="source", label="Heard from", fieldtype="Data"),
	frappe._dict(fieldname="attendees", label="Attendees", fieldtype="Number"),
	frappe._dict(fieldname="start", label="Start", fieldtype="Date"),
]


def answers(**values) -> list[dict]:
	return [{"fieldname": key, "label": key, "value": value} for key, value in values.items()]


class TestListConditions(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.event = BuzzEventFactory.create().name
		cls.yes = cls.enquiry(
			"Approval Pending",
			booth="1",
			size="200+",
			interests=json.dumps(["Talk", "Swag"]),
			source="Twitter",
			attendees="12",
			start=add_days(today(), 10),
		)
		cls.no = cls.enquiry(
			"Paid",
			booth="0",
			size="11-50",
			interests=json.dumps(["Swag"]),
			source="Newsletter",
			attendees="3",
			start=add_days(today(), 40),
		)
		cls.blank = cls.enquiry("Paid")

	@classmethod
	def enquiry(cls, status: str, **values) -> str:
		return SponsorshipEnquiryFactory.create(
			event=cls.event, status=status, additional_fields=answers(**values)
		).name

	def matching(self, *triples) -> set[str]:
		fields = [filter_field("status", "Status", "Select", [("Paid", "Paid")]), *question_fields(QUESTIONS)]
		conditions = ListConditions("Sponsorship Enquiry", fields).frappe_filters(json.dumps(triples))
		filters = [["event", "=", self.event], *conditions]
		return set(frappe.get_all("Sponsorship Enquiry", filters=filters, pluck="name"))

	def test_standard_field_passes_through(self):
		self.assertEqual(self.matching(["status", "in", ["Paid"]]), {self.no, self.blank})

	def test_check_no_includes_unanswered(self):
		self.assertEqual(self.matching(["booth", "in", ["1"]]), {self.yes})
		self.assertEqual(self.matching(["booth", "in", ["0"]]), {self.no, self.blank})

	def test_select_is_and_is_not(self):
		self.assertEqual(self.matching(["size", "in", ["200+"]]), {self.yes})
		self.assertEqual(self.matching(["size", "not in", ["200+"]]), {self.no, self.blank})

	def test_multi_select_includes_and_excludes(self):
		self.assertEqual(self.matching(["interests", "like", ["Talk"]]), {self.yes})
		self.assertEqual(self.matching(["interests", "not like", ["Talk"]]), {self.no, self.blank})

	def test_text_contains_and_exact(self):
		self.assertEqual(self.matching(["source", "like", "twit"]), {self.yes})
		self.assertEqual(self.matching(["source", "not like", "twit"]), {self.no, self.blank})
		self.assertEqual(self.matching(["source", "=", "Newsletter"]), {self.no})

	def test_numbers_compare_as_numbers(self):
		self.assertEqual(self.matching(["attendees", ">", "5"]), {self.yes})
		self.assertEqual(self.matching(["attendees", "between", ["1", "5"]]), {self.no})

	def test_dates_compare(self):
		self.assertEqual(self.matching(["start", "<", add_days(today(), 20)]), {self.yes})

	def test_answered_and_not_answered(self):
		self.assertEqual(self.matching(["source", "is", "set"]), {self.yes, self.no})
		self.assertEqual(self.matching(["source", "is", "not set"]), {self.blank})

	def test_conditions_on_two_questions_combine(self):
		self.assertEqual(self.matching(["size", "in", ["11-50"]], ["source", "like", "news"]), {self.no})

	def test_empty_value_filters_nothing(self):
		everyone = {self.yes, self.no, self.blank}
		self.assertEqual(self.matching(["source", "like", ""]), everyone)
		self.assertEqual(self.matching(["attendees", "between", ["1", ""]]), everyone)

	def test_unknown_field_or_operator_is_rejected(self):
		with self.assertRaises(InvalidFilter):
			self.matching(["company_name", "like", "x"])
		with self.assertRaises(InvalidFilter):
			self.matching(["status", "like", "Paid"])
		with self.assertRaises(InvalidFilter):
			self.matching([["status"], "in", ["Paid"]])
