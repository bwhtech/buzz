import frappe
from frappe.tests import UnitTestCase

from buzz.api.forms.answers import CustomAnswers
from buzz.api.forms.conditions import all_conditions_match, is_required, is_shown


def question(**fields) -> frappe._dict:
	return frappe._dict(
		{
			"label": "Budget",
			"fieldname": "budget",
			"mandatory": 0,
			"depends_on": None,
			"mandatory_depends_on": None,
			**fields,
		}
	)


class TestMatches(UnitTestCase):
	def test_no_conditions_always_match(self):
		self.assertTrue(all_conditions_match(None, {}))
		self.assertTrue(all_conditions_match([], {"tier": "Gold"}))
		self.assertTrue(all_conditions_match("[]", {"tier": "Gold"}))

	def test_equals_and_not_equals(self):
		condition = [["tier", "=", "Gold"]]

		self.assertTrue(all_conditions_match(condition, {"tier": "Gold"}))
		self.assertFalse(all_conditions_match(condition, {"tier": "Silver"}))
		self.assertTrue(all_conditions_match([["tier", "!=", "Gold"]], {"tier": "Silver"}))
		self.assertFalse(all_conditions_match([["tier", "!=", "Gold"]], {"tier": "Gold"}))

	def test_in_and_not_in(self):
		condition = [["tier", "in", ["Gold", "Silver"]]]

		self.assertTrue(all_conditions_match(condition, {"tier": "Gold"}))
		self.assertFalse(all_conditions_match(condition, {"tier": "Bronze"}))
		self.assertTrue(all_conditions_match([["tier", "not in", ["Gold"]]], {"tier": "Bronze"}))
		self.assertFalse(all_conditions_match([["tier", "not in", ["Gold"]]], {"tier": "Gold"}))

	def test_comparisons(self):
		cases = [
			(">", 6000, True),
			(">", 5000, False),
			(">=", 5000, True),
			(">=", 4000, False),
			("<", 4000, True),
			("<", 5000, False),
			("<=", 5000, True),
			("<=", 6000, False),
		]
		for operator, value, expected in cases:
			with self.subTest(operator=operator, value=value):
				self.assertIs(all_conditions_match([["budget", operator, 5000]], {"budget": value}), expected)

	def test_comparisons_read_text_and_blank_answers_as_numbers(self):
		self.assertTrue(all_conditions_match([["budget", ">", 5000]], {"budget": "6000"}))
		self.assertFalse(all_conditions_match([["budget", ">", 5000]], {}))

	def test_is_set_and_is_not_set(self):
		self.assertTrue(all_conditions_match([["tier", "is", "set"]], {"tier": "Gold"}))
		self.assertFalse(all_conditions_match([["tier", "is", "set"]], {"tier": None}))
		self.assertFalse(all_conditions_match([["tier", "is", "set"]], {}))
		self.assertTrue(all_conditions_match([["tier", "is", "not set"]], {}))
		self.assertFalse(all_conditions_match([["tier", "is", "not set"]], {"tier": "Gold"}))

	def test_every_triple_must_match(self):
		condition = [["tier", "=", "Gold"], ["budget", ">", 5000]]

		self.assertTrue(all_conditions_match(condition, {"tier": "Gold", "budget": 6000}))
		self.assertFalse(all_conditions_match(condition, {"tier": "Gold", "budget": 4000}))
		self.assertFalse(all_conditions_match(condition, {"tier": "Silver", "budget": 6000}))

	def test_json_conditions_are_read(self):
		self.assertTrue(all_conditions_match('[["tier", "=", "Gold"]]', {"tier": "Gold"}))

	def test_multi_select_matches_when_any_item_is_in_the_list(self):
		condition = [["topics", "in", ["ai", "web"]]]

		self.assertTrue(all_conditions_match(condition, {"topics": ["web", "ops"]}))
		self.assertFalse(all_conditions_match(condition, {"topics": ["ops"]}))
		self.assertTrue(all_conditions_match([["topics", "not in", ["ai"]]], {"topics": ["ops"]}))
		self.assertFalse(all_conditions_match([["topics", "not in", ["ai"]]], {"topics": ["ai", "ops"]}))


class TestShowingAndRequiring(UnitTestCase):
	def test_a_question_without_conditions_is_shown(self):
		self.assertTrue(is_shown(question(), {}))

	def test_a_question_is_hidden_until_its_conditions_match(self):
		hidden = question(depends_on=[["tier", "=", "Gold"]])

		self.assertTrue(is_shown(hidden, {"tier": "Gold"}))
		self.assertFalse(is_shown(hidden, {"tier": "Silver"}))

	def test_required_when_mandatory_or_its_condition_matches(self):
		always = question(mandatory=1)
		conditional = question(mandatory_depends_on=[["tier", "=", "Gold"]])

		self.assertTrue(is_required(always, {}))
		self.assertFalse(is_required(question(), {}))
		self.assertTrue(is_required(conditional, {"tier": "Gold"}))
		self.assertFalse(is_required(conditional, {"tier": "Silver"}))

	def test_a_hidden_question_is_never_required(self):
		hidden = question(mandatory=1, depends_on=[["tier", "=", "Gold"]])

		self.assertFalse(is_required(hidden, {"tier": "Silver"}))
		self.assertTrue(is_required(hidden, {"tier": "Gold"}))


class TestAnswerRows(UnitTestCase):
	def test_a_hidden_answer_does_not_steer_later_questions(self):
		"""The stale answer of a hidden question must not make a question below it required."""
		sponsor = question(label="Sponsor?", fieldname="sponsor", depends_on=[["tier", "=", "Gold"]])
		budget = question(mandatory_depends_on=[["sponsor", "=", "yes"]])
		answers = CustomAnswers([answer_definition(sponsor), answer_definition(budget)])

		self.assertEqual(answers.rows({"sponsor": "yes"}, context={"tier": "Silver"}), [])


def answer_definition(row) -> frappe._dict:
	return frappe._dict({**row, "enabled": 1, "fieldtype": "Data"})
