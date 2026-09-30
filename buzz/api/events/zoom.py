from buzz.api.events.exceptions import EventEnded, ZoomNotAvailable
from buzz.api.events.services import manageable_event
from buzz.utils import is_app_installed


def convert_to_zoom_meeting(event: str) -> None:
	"""Make the event virtual on a Zoom meeting, or leave it as it was.

	The event is saved before the meeting is booked, so a failed save never leaves a meeting
	behind on Zoom, and a Zoom failure rolls the save back with the request.
	A meeting still linked from an earlier conversion is reused rather than booked twice.
	"""
	# buzz.www.events imports the event page, which imports this package.
	from buzz.www.events import has_ended

	doc = manageable_event(event)
	if not is_app_installed("zoom_integration"):
		ZoomNotAvailable.throw()
	if has_ended(doc):
		EventEnded.throw()

	doc.medium = "Online"
	# The organiser's own link outranks Zoom's in `meeting_link_of`.
	doc.meeting_link = None
	doc.save()
	if not doc.zoom_meeting:
		doc.create_meeting_on_zoom()
