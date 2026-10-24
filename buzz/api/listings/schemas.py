from pydantic import AwareDatetime

from buzz.api.communities.schemas import ExternalEvent, Text140


class EventListing(ExternalEvent):
	"""An event a partner site lists on its community page."""

	source_id: Text140
	start_datetime: AwareDatetime
	end_datetime: AwareDatetime
