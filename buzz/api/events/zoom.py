from buzz.api.events.exceptions import EventEnded, ZoomNotAvailable
from buzz.api.events.services import manageable_event
from buzz.utils import is_app_installed
from buzz.www.events import has_ended


def convert_to_zoom_meeting(event: str) -> None:
	"""Make the event virtual on a Zoom meeting, or leave it as it was.

	The meeting is booked before the medium changes, so a Zoom failure changes nothing.
	A meeting still linked from an earlier conversion is reused rather than booked twice.
	"""
	doc = manageable_event(event)
	if not is_app_installed("zoom_integration"):
		ZoomNotAvailable.throw()
	if has_ended(doc):
		EventEnded.throw()

	if not doc.zoom_meeting:
		doc.create_meeting_on_zoom()
	doc.medium = "Online"
	# The organiser's own link outranks Zoom's in `meeting_link_of`.
	doc.meeting_link = None
	doc.save()
