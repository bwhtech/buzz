from pydantic import AwareDatetime, Field

from buzz.api.communities.schemas import ExternalEvent, Text140


class EventListing(ExternalEvent):
	"""An event a partner site lists on its community page."""

	source_id: Text140
	latitude: float | None = Field(default=None, ge=-90, le=90)
	longitude: float | None = Field(default=None, ge=-180, le=180)
	city: Text140 | None = None
	country: Text140 | None = None
	start_datetime: AwareDatetime
	end_datetime: AwareDatetime
