from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import set_request
from frappe.website.serve import get_response_content

from buzz.www.site_header import BUZZ_FOOTER, buzz_navbar


class TestBuzzFooter(IntegrationTestCase):
	def test_frappe_page_renders_buzz_footer_with_the_buzz_brand(self):
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		set_request(method="GET", path="/login")
		# CI never runs bench build, so there is no assets.json for bundled_asset to read
		with (
			self.change_settings("Website Settings", footer_template=BUZZ_FOOTER),
			patch("frappe.utils.get_assets_json", return_value={}),
		):
			html = get_response_content("/login")
		self.assertIn("buzz-footer", html)
		self.assertIn(buzz_navbar()["brand"]["name"], html)
