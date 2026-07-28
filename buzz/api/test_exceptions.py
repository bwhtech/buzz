import frappe
from frappe import _lt
from frappe.tests import IntegrationTestCase

from buzz.api.exceptions import BuzzAPIError, Conflict, NotPermitted, ResourceNotFound


class Parameterized(BuzzAPIError):
	http_status_code = 418
	title = _lt("Teapot")
	message = _lt("{item} is not available.")


class TestBuzzAPIError(IntegrationTestCase):
	def setUp(self):
		frappe.clear_messages()

	def last_message(self) -> dict:
		return frappe.local.message_log[-1]

	def test_throw_raises_its_own_class(self):
		with self.assertRaises(Conflict):
			Conflict.throw()

	def test_throw_publishes_title_and_message(self):
		with self.assertRaises(Conflict):
			Conflict.throw()

		self.assertEqual(self.last_message()["title"], "Not Allowed")
		self.assertIn("conflicts", self.last_message()["message"])

	def test_message_accepts_context(self):
		with self.assertRaises(Parameterized):
			Parameterized.throw(item="Chai")

		self.assertEqual(self.last_message()["message"], "Chai is not available.")

	def test_bare_raise_publishes_nothing(self):
		# A bare raise skips msgprint, so the dashboard would show "Internal Server Error".
		with self.assertRaises(Conflict):
			raise Conflict

		self.assertEqual(frappe.local.message_log, [])

	def test_status_codes(self):
		self.assertEqual(BuzzAPIError.http_status_code, 400)
		self.assertEqual(ResourceNotFound.http_status_code, 404)
		self.assertEqual(NotPermitted.http_status_code, 403)
		self.assertEqual(Conflict.http_status_code, 409)

	def test_subclass_inherits_status_code(self):
		self.assertEqual(Parameterized.http_status_code, 418)

	def test_errors_are_validation_errors(self):
		# Keeps existing `except frappe.ValidationError` handlers working.
		self.assertTrue(issubclass(BuzzAPIError, frappe.ValidationError))
