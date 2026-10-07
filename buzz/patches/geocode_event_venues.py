from buzz.events.doctype.event_venue.geocode import enqueue_geocode_batch, venues_to_geocode


def execute():
	"""Venues saved before geocoding have no city or country; fill them in the background."""
	enqueue_geocode_batch(venues_to_geocode())
