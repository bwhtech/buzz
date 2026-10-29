import frappe
from frappe import _
from frappe.utils import cstr

from buzz.api.schedule.schemas import ScheduleTalk

DEFAULT_TRACK_TITLE = "Main hall"
DEFAULT_TRACK_COLOR = "blue"


def get_or_create_schedule(event: int) -> str:
	name = frappe.db.get_value("Buzz Schedule", {"event": event})
	return name or create_schedule(event)


def create_schedule(event: int) -> str:
	schedule = frappe.get_doc({"doctype": "Buzz Schedule", "event": event}).insert()
	frappe.get_doc(
		{
			"doctype": "Buzz Schedule Track",
			"schedule": schedule.name,
			"title": _(DEFAULT_TRACK_TITLE),
			"color": DEFAULT_TRACK_COLOR,
		}
	).insert()
	return schedule.name


def unscheduled_talks(event: int) -> list[ScheduleTalk]:
	scheduled = frappe.get_all(
		"Buzz Schedule Item",
		filters={"parenttype": "Buzz Schedule", "reference_doctype": "Event Talk"},
		pluck="reference_document",
	)
	talks = frappe.get_list(
		"Event Talk",
		filters={"event": event, "name": ["not in", scheduled or [""]]},
		fields=["name", "title"],
		order_by="title",
	)
	speakers = speaker_names([talk.name for talk in talks])
	return [
		ScheduleTalk(name=str(talk.name), title=cstr(talk.title), speakers=speakers.get(talk.name, ""))
		for talk in talks
	]


def speaker_names(talks: list[str]) -> dict[str, str]:
	rows = frappe.get_all(
		"Talk Speaker",
		filters={"parenttype": "Event Talk", "parent": ["in", talks or [""]]},
		fields=["parent", "speaker"],
		order_by="idx",
	)
	profiles = frappe.get_all(
		"Speaker Profile",
		filters={"name": ["in", [row.speaker for row in rows] or [""]]},
		fields=["name", "display_name"],
	)
	display_names = {str(profile.name): profile.display_name for profile in profiles}
	names: dict[str, list[str]] = {}
	for row in rows:
		names.setdefault(str(row.parent), []).append(display_names.get(str(row.speaker), row.speaker))
	return {talk: ", ".join(labels) for talk, labels in names.items()}
