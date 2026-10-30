from frappe.tests import UnitTestCase

from buzz.www.event.dot_map import ASPECT_RATIO, MINIMUM_VIEW_WIDTH, DotMap

BENGALURU = (12.97, 77.59)
MUMBAI = (19.06, 72.87)
SAN_FRANCISCO = (37.78, -122.40)
BERLIN = (52.54, 13.39)


class TestDotMap(UnitTestCase):
	def test_view_frames_every_pin_at_the_map_aspect_ratio(self):
		dot_map = DotMap([BENGALURU, MUMBAI, SAN_FRANCISCO, BERLIN])

		for latitude, longitude in [BENGALURU, MUMBAI, SAN_FRANCISCO, BERLIN]:
			pin = dot_map.pin(latitude, longitude)
			self.assertTrue(0 < pin["x"] < 100 and 0 < pin["y"] < 100, pin)
		self.assertAlmostEqual(dot_map.view.width / dot_map.view.height, ASPECT_RATIO)

	def test_nearby_pins_zoom_in_no_closer_than_the_minimum_width(self):
		dot_map = DotMap([BENGALURU, MUMBAI])

		self.assertEqual(dot_map.view.width, MINIMUM_VIEW_WIDTH)
		self.assertNotEqual(dot_map.pin(*BENGALURU), dot_map.pin(*MUMBAI))

	def test_a_wide_view_uses_the_coarse_dots(self):
		self.assertIn("coarse", DotMap([SAN_FRANCISCO, BENGALURU]).dots_url)
		self.assertNotIn("coarse", DotMap([BENGALURU, MUMBAI]).dots_url)
