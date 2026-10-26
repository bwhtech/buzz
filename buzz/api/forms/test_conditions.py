import frappe
from frappe.tests import UnitTestCase

from buzz.api.forms.conditions import is_required, is_shown, matches


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
		self.assertTrue(matches(None, {}))
		self.assertTrue(matches([], {"tier": "Gold"}))
		self.assertTrue(matches("[]", {"tier": "Gold"}))

	def test_equals_and_not_equals(self):
		condition = [["tier", "=", "Gold"]]

		self.assertTrue(matches(condition, {"tier": "Gold"}))
		self.assertFalse(matches(condition, {"tier": "Silver"}))
		self.assertTrue(matches([["tier", "!=", "Gold"]], {"tier": "Silver"}))
		self.assertFalse(matches([["tier", "!=", "Gold"]], {"tier": "Gold"}))

	def test_in_and_not_in(self):
		condition = [["tier", "in", ["Gold", "Silver"]]]

		self.assertTrue(matches(condition, {"tier": "Gold"}))
		self.assertFalse(matches(condition, {"tier": "Bronze"}))
		self.assertTrue(matches([["tier", "not in", ["Gold"]]], {"tier": "Bronze"}))
		self.assertFalse(matches([["tier", "not in", ["Gold"]]], {"tier": "Gold"}))

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
				self.assertIs(matches([["budget", operator, 5000]], {"budget": value}), expected)

	def test_comparisons_read_text_and_blank_answers_as_numbers(self):
		self.assertTrue(matches([["budget", ">", 5000]], {"budget": "6000"}))
		self.assertFalse(matches([["budget", ">", 5000]], {}))

	def test_is_set_and_is_not_set(self):
		self.assertTrue(matches([["tier", "is", "set"]], {"tier": "Gold"}))
		self.assertFalse(matches([["tier", "is", "set"]], {"tier": None}))
		self.assertFalse(matches([["tier", "is", "set"]], {}))
		self.assertTrue(matches([["tier", "is", "not set"]], {}))
		self.assertFalse(matches([["tier", "is", "not set"]], {"tier": "Gold"}))

	def test_every_triple_must_match(self):
		condition = [["tier", "=", "Gold"], ["budget", ">", 5000]]

		self.assertTrue(matches(condition, {"tier": "Gold", "budget": 6000}))
		self.assertFalse(matches(condition, {"tier": "Gold", "budget": 4000}))
		self.assertFalse(matches(condition, {"tier": "Silver", "budget": 6000}))

	def test_json_conditions_are_read(self):
		self.assertTrue(matches('[["tier", "=", "Gold"]]', {"tier": "Gold"}))

	def test_multi_select_matches_when_any_item_is_in_the_list(self):
		condition = [["topics", "in", ["ai", "web"]]]

		self.assertTrue(matches(condition, {"topics": ["web", "ops"]}))
		self.assertFalse(matches(condition, {"topics": ["ops"]}))
		self.assertTrue(matches([["topics", "not in", ["ai"]]], {"topics": ["ops"]}))
		self.assertFalse(matches([["topics", "not in", ["ai"]]], {"topics": ["ai", "ops"]}))


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
