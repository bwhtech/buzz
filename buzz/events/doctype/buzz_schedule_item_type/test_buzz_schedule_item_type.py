# Copyright (c) 2026, BWH Studios and contributors
# For license information, please see license.txt

import frappe

from buzz.tests.base_test_cases import TeamPermissionTestCase
from buzz.tests.factories import BuzzScheduleItemTypeFactory


class TestBuzzScheduleItemType(TeamPermissionTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.type_a = BuzzScheduleItemTypeFactory.create(team=cls.team_a).name

	def test_other_team_cannot_list_or_read_custom_types(self):
		self.assertIn(self.type_a, self.list_as(self.alice, "Buzz Schedule Item Type"))
		self.assertNotIn(self.type_a, self.list_as(self.bob, "Buzz Schedule Item Type"))
		self.assertFalse(self.has_permission_as(self.bob, "read", "Buzz Schedule Item Type", self.type_a))

	def test_every_team_sees_standard_types(self):
		self.assertIn("Talk", self.list_as(self.bob, "Buzz Schedule Item Type"))
		self.assertTrue(self.has_permission_as(self.bob, "read", "Buzz Schedule Item Type", "Talk"))

	def test_team_member_cannot_write_standard_types(self):
		self.assertFalse(self.has_permission_as(self.alice, "write", "Buzz Schedule Item Type", "Talk"))

	def test_color_must_be_a_theme_name_or_hex(self):
		BuzzScheduleItemTypeFactory.create(team=self.team_a, color="#2563eb")
		with self.assertRaises(frappe.ValidationError):
			BuzzScheduleItemTypeFactory.create(team=self.team_a, color="sky")
