import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import get_url
from frappe.website.serve import get_response

from buzz.tests.factories import BuzzEventFactory


class TestEventsSitemap(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.published = BuzzEventFactory.create().route
		cls.unpublished = BuzzEventFactory.create("unpublished").route

	def setUp(self):
		frappe.set_user("Guest")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_lists_only_published_events(self):
		body = get_response("events-sitemap.xml").get_data(as_text=True)
		self.assertIn(f"<loc>{get_url(f'/events/{self.published}')}</loc>", body)
		self.assertNotIn(f"/events/{self.unpublished}<", body)

	def test_serves_xml(self):
		response = get_response("events-sitemap.xml")
		self.assertEqual(response.status_code, 200)
		self.assertIn("xml", response.headers["Content-Type"])
