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
