import json
from pathlib import Path

import frappe
from frappe.tests import UnitTestCase

from buzz.api.forms.answers import CustomAnswers
from buzz.api.forms.conditions import FormLogic, condition_matches

# Shared with dashboard/src/utils/formLogic.test.ts, so both evaluators agree.
CASES = json.loads((Path(__file__).parent / "logic_cases.json").read_text())


def question(fieldname: str, mandatory: int = 0) -> frappe._dict:
	return frappe._dict(
		label=fieldname.title(), fieldname=fieldname, fieldtype="Data", mandatory=mandatory, enabled=1
	)


class TestSharedCases(UnitTestCase):
	def test_conditions(self):
		for case in CASES["conditions"]:
			with self.subTest(case["condition"], values=case["values"]):
				self.assertIs(condition_matches(case["condition"], case["values"]), case["expected"])

	def test_forms(self):
		for case in CASES["forms"]:
			logic = FormLogic(case["rules"])
			for fieldname, expected in case["questions"].items():
				with self.subTest(case["name"], fieldname=fieldname):
					row = question(fieldname, expected["mandatory"])
					self.assertIs(logic.is_shown(row, case["values"]), expected["shown"])
					self.assertIs(logic.is_required(row, case["values"]), expected["required"])


SHOW_BUDGET_FOR_GOLD = [
	{"match": "all", "conditions": [["tier", "=", "Gold"]], "actions": [["show", "budget"]]}
]


class TestAnswersFollowRules(UnitTestCase):
	def test_hidden_question_is_not_required_and_its_answer_is_dropped(self):
		answers = CustomAnswers([question("budget", mandatory=1)], SHOW_BUDGET_FOR_GOLD)

		self.assertEqual(answers.rows({"budget": "9000"}, context={"tier": "Silver"}), [])

	def test_shown_question_is_enforced(self):
		answers = CustomAnswers([question("budget", mandatory=1)], SHOW_BUDGET_FOR_GOLD)

		with self.assertRaises(frappe.MandatoryError):
			answers.rows({}, context={"tier": "Gold"})

	def test_conditions_read_only_shown_answers_above(self):
		rules = [
			*SHOW_BUDGET_FOR_GOLD,
			{"match": "all", "conditions": [["budget", "is", "set"]], "actions": [["require", "company"]]},
		]
		answers = CustomAnswers([question("budget"), question("company")], rules)

		# Budget is hidden for Silver, so its stale answer cannot make company required.
		self.assertEqual(answers.rows({"budget": "9000"}, context={"tier": "Silver"}), [])
