from frappe.tests import UnitTestCase

from buzz.www.event.dot_map import pin_position


class TestDotMapPins(UnitTestCase):
	def test_pins_land_where_the_map_puts_their_coordinates(self):
		cases = {
			"top left corner": ((84, -180), {"x": 0, "y": 0}),
			"bottom right corner": ((-56, 180), {"x": 100, "y": 100}),
			"centre": ((14, 0), {"x": 50, "y": 50}),
			"below the map is kept on it": ((-75, 0), {"x": 50, "y": 100}),
		}
		for case, ((latitude, longitude), position) in cases.items():
			with self.subTest(case):
				self.assertEqual(pin_position(latitude, longitude), position)
