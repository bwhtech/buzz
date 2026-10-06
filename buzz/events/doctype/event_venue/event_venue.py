# Copyright (c) 2025, BWH Studios and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document

from buzz.events.doctype.event_venue.geocode import enqueue_geocode, needs_geocoding
from buzz.events.doctype.event_venue.map_link import read_map_link
from buzz.www.event.venue_map import google_maps_url


class EventVenue(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.SmallText | None
		city: DF.Data | None
		google_maps_embed_code: DF.Code | None
		google_place_id: DF.Data | None
		latitude: DF.Float
		longitude: DF.Float
		map_link: DF.SmallText | None
		team: DF.Link | None
		venue_country: DF.Link | None
		venue_name: DF.Data
		type: DF.Literal["Embed Google Maps", "Open Street Map"]
	# end: auto-generated types

	def validate(self):
		self.set_location_from_map_link()
		self.validate_address()
		self.set_geojson_for_location()
		self.remove_fixed_dimensions_from_google_map_embed()

	def on_update(self):
		# A live worker would call Nominatim mid-test.
		if frappe.in_test or self.flags.geocoded or not needs_geocoding(self):
			return
		if self.has_value_changed("address") or self.has_value_changed("latitude"):
			enqueue_geocode(self.name)

	def set_location_from_map_link(self):
		if not self.map_link or not self.has_value_changed("map_link"):
			return
		if google_maps_url(self.map_link):
			self.type = "Embed Google Maps"
			self.google_maps_embed_code = self.map_link
			return
		place = read_map_link(self.map_link)
		if place.coordinates:
			self.type = "Open Street Map"
			self.latitude, self.longitude = place.coordinates
			self.address = self.address or place.address

	def validate_address(self):
		has_location = (self.latitude and self.longitude) or self.google_maps_embed_code
		if not self.address and not has_location:
			frappe.throw(_("Add an address, or a map link that shows where the venue is."))

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


def set_venue_names(rows: list) -> None:
	"""Swap each row's `venue` from the venue's random name to its label."""
	venues = [row.venue for row in rows if row.venue]
	names = {}
	if venues:
		names = dict(
			frappe.get_all(
				"Event Venue", filters={"name": ["in", venues]}, fields=["name", "venue_name"], as_list=True
			)
		)
	for row in rows:
		row.venue = names.get(row.venue)
