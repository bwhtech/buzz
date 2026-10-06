# Copyright (c) 2026, BWH Studios and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from buzz.tests.factories import BuzzEventFactory, OfflinePaymentMethodFactory


class TestOfflinePaymentMethod(IntegrationTestCase):
	def test_unique_title_per_event(self):
		event = BuzzEventFactory.create().name
		OfflinePaymentMethodFactory.create(event=event, title="Bank Transfer")

		with self.assertRaises(frappe.ValidationError):
			OfflinePaymentMethodFactory.create(event=event, title="Bank Transfer")

	def test_same_title_different_events(self):
		first, second = BuzzEventFactory.create_list(2)
		OfflinePaymentMethodFactory.create(event=first.name, title="UPI Payment")

		method = OfflinePaymentMethodFactory.create(event=second.name, title="UPI Payment")

		self.assertEqual(method.title, "UPI Payment")
