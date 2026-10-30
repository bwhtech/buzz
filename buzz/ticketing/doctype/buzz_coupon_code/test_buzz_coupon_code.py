# Copyright (c) 2025, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, today

from buzz.tests.base_test_cases import CouponTestCase
from buzz.tests.factories import BuzzCouponCodeFactory, BuzzEventFactory, EventTicketTypeFactory


class TestCouponValidation(CouponTestCase):
	def test_event_is_required(self):
		with self.assertRaises(frappe.MandatoryError):
			BuzzCouponCodeFactory.create(event=None)

	def test_code_is_stripped_and_uppercased(self):
		coupon = self.create_coupon(code="  summer10 ")

		self.assertEqual(coupon.code, "SUMMER10")

	def test_promo_code_needs_a_code(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(code=None)

	def test_duplicate_code_on_same_event_rejected(self):
		self.create_coupon(code="DUPLICATE", enabled=0)

		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(code="duplicate")

	def test_same_code_on_another_event_allowed(self):
		self.create_coupon(code="SHARED")

		coupon = BuzzCouponCodeFactory.create(code="SHARED")

		self.assertEqual(coupon.code, "SHARED")

	def test_promo_code_rejects_spaces_and_symbols(self):
		for code in ("EARLY BIRD", "SAVE20%", "HI!"):
			with self.subTest(code=code), self.assertRaises(frappe.ValidationError):
				self.create_coupon(code=code)

	def test_promo_code_allows_hyphens_and_underscores(self):
		self.assertEqual(self.create_coupon(code="early-bird_26").code, "EARLY-BIRD_26")

	def test_automatic_coupon_keeps_its_name_as_typed(self):
		coupon = self.create_coupon("automatic", code=" Group of 5+ ")

		self.assertEqual(coupon.code, "Group of 5+")

	def test_automatic_coupon_needs_a_name(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon("automatic", code=" ")

	def test_start_after_expiry_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(starts_on=add_days(today(), 5), expires_on=add_days(today(), 2))

	def test_percentage_must_be_above_zero(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(discount_percentage=0)

	def test_percentage_cannot_exceed_100(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(discount_percentage=150)

	def test_flat_amount_needs_a_row(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon("flat", discount_amounts=[])

	def test_flat_amount_must_be_positive(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon("flat", discount_amounts=[{"currency": "INR", "price": 0}])

	def test_flat_amount_currencies_must_be_unique(self):
		rows = [{"currency": "INR", "price": 100}, {"currency": "INR", "price": 200}]

		with self.assertRaises(frappe.ValidationError):
			self.create_coupon("flat", discount_amounts=rows)

	def test_scoped_coupon_needs_ticket_types(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(applies_to_all_ticket_types=0, ticket_types=[])

	def test_ticket_type_from_another_event_rejected(self):
		other = EventTicketTypeFactory.create(event=BuzzEventFactory.create().name)

		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(applies_to_all_ticket_types=0, ticket_types=[{"ticket_type": other.name}])

	def test_minimum_order_amount_needs_a_row(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(minimum_requirement="Minimum Order Amount", minimum_order_amounts=[])

	def test_minimum_ticket_count_must_be_positive(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_coupon(minimum_requirement="Minimum Ticket Count", minimum_ticket_count=0)

	def test_find_by_code_ignores_case_and_event(self):
		coupon = self.create_coupon(code="FINDME")
		BuzzCouponCodeFactory.create(code="FINDME")

		self.assertEqual(type(coupon).find_by_code(self.event.name, " findme").name, coupon.name)
		self.assertIsNone(type(coupon).find_by_code(self.event.name, "MISSING"))

	def test_find_by_code_skips_automatic_coupons(self):
		coupon = self.create_coupon("automatic", code="Group deal")

		self.assertIsNone(type(coupon).find_by_code(self.event.name, "GROUP DEAL"))


class TestAccessCodeValidation(CouponTestCase):
	def setUp(self):
		self.hidden = EventTicketTypeFactory.create("is_hidden", event=self.event.name)

	def create_access_code(self, **overrides):
		overrides.setdefault("ticket_types", [{"ticket_type": self.hidden.name}])
		return self.create_coupon("access_code", **overrides)

	def test_no_discount_is_refused_on_promo_and_automatic_codes(self):
		for traits in ((), ("automatic",)):
			with self.subTest(traits=traits), self.assertRaises(frappe.ValidationError):
				self.create_coupon(*traits, discount_type="None")

	def test_access_code_is_uppercased_and_unlocks_its_scope(self):
		coupon = self.create_access_code(code=" press-2026 ")

		self.assertEqual(coupon.code, "PRESS-2026")
		self.assertEqual(coupon.unlocked_ticket_types(), {str(self.hidden.name)})
		self.assertEqual(type(coupon).find_by_code(self.event.name, "press-2026").name, coupon.name)

	def test_access_code_is_never_scoped_to_all_ticket_types(self):
		coupon = self.create_access_code(applies_to_all_ticket_types=1)

		self.assertEqual(coupon.applies_to_all_ticket_types, 0)

	def test_access_code_with_a_public_ticket_type_in_scope_is_refused(self):
		scope = [{"ticket_type": self.hidden.name}, {"ticket_type": self.ticket_type.name}]

		with self.assertRaises(frappe.ValidationError):
			self.create_access_code(ticket_types=scope)

	def test_access_code_with_an_empty_scope_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.create_access_code(ticket_types=[])

	def test_access_code_may_carry_a_discount(self):
		coupon = self.create_access_code(discount_type="Percentage", discount_percentage=20)

		self.assertEqual(coupon.discount_percentage, 20)

	def test_other_coupon_types_unlock_nothing(self):
		self.assertEqual(self.create_coupon().unlocked_ticket_types(), set())
