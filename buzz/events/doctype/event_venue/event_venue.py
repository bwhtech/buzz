# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


class EventVenue(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.SmallText
		google_maps_embed_code: DF.Code | None
		latitude: DF.Float
		longitude: DF.Float
		team: DF.Link
		type: DF.Literal["Embed Google Maps", "Open Street Map"]
	# end: auto-generated types

	def validate(self):
		self.set_geojson_for_location()
		self.remove_fixed_dimensions_from_google_map_embed()

	def remove_fixed_dimensions_from_google_map_embed(self):
		if not self.google_maps_embed_code:
			return

		html = self.google_maps_embed_code
		html = re.sub(r'height="(\d+)"', r'height="100%"', html)
		html = re.sub(r'width="(\d+)"', r'width="100%"', html)

		self.google_maps_embed_code = html

	def set_geojson_for_location(self):
		if self.latitude and self.longitude:
			self.location = {
				"type": "FeatureCollection",
				"features": [
					{
						"type": "Feature",
						"properties": {},
						"geometry": {
							"type": "Point",
							"coordinates": [self.longitude, self.latitude],
						},
					}
				],
			}
			self.location = frappe.as_json(self.location)
