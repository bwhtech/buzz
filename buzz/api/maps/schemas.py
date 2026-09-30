from buzz.api.schemas import APIResponse


class MapLinkLocation(APIResponse):
	"""What a pasted map link says about a place; every part may be missing."""

	latitude: float | None = None
	longitude: float | None = None
	name: str | None = None
	address: str | None = None
	embed_url: str | None = None


class PlacePrediction(APIResponse):
	place_id: str
	name: str
	address: str | None = None
