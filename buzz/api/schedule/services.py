import frappe
from frappe import _
from frappe.utils import cstr

from buzz.api.schedule.schemas import ScheduleTalk


def get_or_create_schedule(event: int) -> str:
	return frappe.db.get_value("Buzz Schedule", {"event": event}) or create_schedule(event)


def create_schedule(event: int) -> str:
	return frappe.get_doc({"doctype": "Buzz Schedule", "event": event}).insert().name


def fork_standard_track(schedule: str, track: str) -> str:
	"""Gives the schedule its own copy of a standard track and moves the schedule's items onto it."""
	standard = frappe.get_doc("Buzz Schedule Track", track)
	if not standard.is_standard:
		frappe.throw(_("Only a standard track can be copied"))
	copy = frappe.get_doc(
		{
			"doctype": "Buzz Schedule Track",
			"schedule": schedule,
			"title": standard.title,
			"color": standard.color,
			"capacity": standard.capacity,
			"sequence": standard.sequence,
		}
	).insert()
	frappe.db.set_value(
		"Buzz Schedule Item",
		{"parenttype": "Buzz Schedule", "parent": schedule, "track": track},
		"track",
		copy.name,
	)
	return copy.name


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
