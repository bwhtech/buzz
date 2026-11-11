from unittest.mock import Mock, patch

from frappe.tests import IntegrationTestCase

from buzz.events.doctype.event_venue.map_link import (
	MapLinkPlace,
	full_google_link,
	parse_map_link,
)

REQUESTS_GET = "buzz.events.doctype.event_venue.map_link.requests.get"


class TestGoogleShortLinkHost(IntegrationTestCase):
	@patch(REQUESTS_GET)
	def test_backslash_before_at_is_refused_without_a_request(self, get):
		place = parse_map_link("https://127.0.0.1:9999\\@maps.app.goo.gl/x")

		self.assertEqual(place, MapLinkPlace())
		self.assertFalse(get.called)

	@patch(REQUESTS_GET)
	def test_userinfo_and_port_are_refused_without_a_request(self, get):
		for link in ("https://user@maps.app.goo.gl/x", "https://maps.app.goo.gl:443/x"):
			with self.subTest(link=link):
				self.assertEqual(parse_map_link(link), MapLinkPlace())
		self.assertFalse(get.called)

	@patch(REQUESTS_GET)
	def test_a_bare_short_link_host_is_requested_once(self, get):
		location = "https://www.google.com/maps/@12.9,77.5,15z"
		get.return_value = Mock(headers={"Location": location})

		self.assertEqual(full_google_link("https://maps.app.goo.gl/abc"), location)
		get.assert_called_once()
		self.assertTrue(get.call_args.args[0].startswith("https://maps.app.goo.gl/"))
		self.assertFalse(get.call_args.kwargs["allow_redirects"])
