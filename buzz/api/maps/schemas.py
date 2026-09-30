from buzz.api.schemas import APIResponse


class PlacePrediction(APIResponse):
	place_id: str
	name: str
	address: str | None = None
