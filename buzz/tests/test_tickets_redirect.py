import frappe
from frappe.tests import UnitTestCase
from frappe.website.path_resolver import resolve_redirect


class TestTicketsRedirect(UnitTestCase):
	def setUp(self):
		frappe.cache.delete_value("website_redirects")

	def redirect_location(self, path: str, query_string: str = "") -> str:
		with self.assertRaises(frappe.Redirect):
			resolve_redirect(path, query_string)
		return frappe.flags.redirect_location

	def test_registrations_page_moves_to_tickets(self):
		self.assertEqual(
			self.redirect_location("b/manage/events/EV-1/registrations"),
			"/b/manage/events/EV-1/tickets",
		)

	def test_query_string_is_kept(self):
		self.assertEqual(
			self.redirect_location("b/manage/events/EV-1/registrations", "lang=hi"),
			"/b/manage/events/EV-1/tickets?lang=hi",
		)

	def test_old_dashboard_links_reach_the_new_redirect(self):
		self.assertEqual(
			self.redirect_location("dashboard/manage/events/EV-1/registrations"),
			"/b/manage/events/EV-1/registrations",
		)

	def test_tickets_page_is_left_alone(self):
		self.assertIsNone(resolve_redirect("b/manage/events/EV-1/tickets", ""))
