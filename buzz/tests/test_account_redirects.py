import frappe
from frappe.tests import UnitTestCase
from frappe.website.path_resolver import resolve_redirect


class TestAccountRedirects(UnitTestCase):
	def setUp(self):
		frappe.cache.delete_value("website_redirects")

	def redirect_location(self, path: str, query_string: str = "") -> str:
		with self.assertRaises(frappe.Redirect):
			resolve_redirect(path, query_string)
		return frappe.flags.redirect_location

	def test_proposals_list_moves_to_manage(self):
		self.assertEqual(self.redirect_location("b/account/proposals"), "/b/manage/proposals")

	def test_proposal_id_opens_its_drawer(self):
		self.assertEqual(
			self.redirect_location("b/account/proposals/PROP-0001"),
			"/b/manage/proposals?proposal=PROP-0001",
		)

	def test_query_string_is_kept_after_the_id(self):
		self.assertEqual(
			self.redirect_location("b/account/proposals/PROP-0001", "lang=hi"),
			"/b/manage/proposals?proposal=PROP-0001&lang=hi",
		)

	def test_tabs_without_an_id_land_on_their_new_page(self):
		cases = {
			"b/account": "/b/manage/events",
			"b/account/bookings": "/b/manage/events",
			"b/account/tickets": "/b/manage/events",
			"b/account/sponsorships": "/b/manage/sponsorship",
		}
		for path, target in cases.items():
			with self.subTest(path=path):
				self.assertEqual(self.redirect_location(path), target)

	def test_ids_open_their_drawer(self):
		cases = {
			"b/account/tickets/TKT-1": "/b/manage/events?ticket=TKT-1",
			"b/account/bookings/BKG-1": "/b/manage/events?booking=BKG-1",
			"b/account/sponsorships/ENQ-1": "/b/manage/sponsorship?enquiry=ENQ-1",
		}
		for path, target in cases.items():
			with self.subTest(path=path):
				self.assertEqual(self.redirect_location(path), target)

	def test_payment_success_flag_survives(self):
		self.assertEqual(
			self.redirect_location("b/account/sponsorships/ENQ-1", "success=true"),
			"/b/manage/sponsorship?enquiry=ENQ-1&success=true",
		)

	def test_old_dashboard_links_reach_the_account_redirects(self):
		self.assertEqual(self.redirect_location("dashboard/account/sponsorships"), "/b/account/sponsorships")

	def test_manage_paths_are_left_alone(self):
		self.assertIsNone(resolve_redirect("b/manage/events", ""))
