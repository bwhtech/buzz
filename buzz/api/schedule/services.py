import frappe
from frappe import _
from frappe.utils import cstr

from buzz.api.schedule.schemas import ScheduleTalk

DEFAULT_TRACK_TITLE = "Main Track"
DEFAULT_TRACK_COLOR = "blue"


def get_or_create_schedule(event: int) -> str:
	name = frappe.db.get_value("Buzz Schedule", {"event": event}) or create_schedule(event)
	ensure_track(name)
	return name


def create_schedule(event: int) -> str:
	return frappe.get_doc({"doctype": "Buzz Schedule", "event": event}).insert().name


def ensure_track(schedule: str) -> None:
	if frappe.db.exists("Buzz Schedule Track", {"schedule": schedule}):
		return
	frappe.get_doc(
		{
			"doctype": "Buzz Schedule Track",
			"schedule": schedule,
			"title": _(DEFAULT_TRACK_TITLE),
			"color": DEFAULT_TRACK_COLOR,
			"sequence": 0,
		}
	).insert()


def event_talks(event: int) -> list[ScheduleTalk]:
	talks = frappe.get_list(
		"Event Talk", filters={"event": event}, fields=["name", "title"], order_by="title"
	)
	speakers = speaker_names([str(talk.name) for talk in talks])
	return [
		ScheduleTalk(name=str(talk.name), title=cstr(talk.title), speakers=speakers.get(str(talk.name), []))
		for talk in talks
	]


def speaker_names(talks: list[str]) -> dict[str, list[str]]:
	return {
		talk: [profile.display_name for profile in profiles]
		for talk, profiles in speaker_profiles(talks).items()
	}


def speaker_profiles(talks: list[str], fields: list[str] | None = None) -> dict[str, list]:
	"""Speaker Profile rows of each talk, in speaker order."""
	rows = frappe.get_all(
		"Talk Speaker",
		filters={"parenttype": "Event Talk", "parent": ["in", talks or [""]]},
		fields=["parent", "speaker"],
		order_by="idx",
	)
	profiles = {
		str(profile.name): profile
		for profile in frappe.get_all(
			"Speaker Profile",
			filters={"name": ["in", [row.speaker for row in rows] or [""]]},
			fields=["name", "display_name", *(fields or [])],
		)
	}
	by_talk: dict[str, list] = {}
	for row in rows:
		if row.speaker in profiles:
			by_talk.setdefault(str(row.parent), []).append(profiles[row.speaker])
	return by_talk
