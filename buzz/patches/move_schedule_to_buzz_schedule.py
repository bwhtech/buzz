import frappe
from frappe import _
from frappe.utils import getdate

from buzz.events.doctype.buzz_schedule.buzz_schedule import event_days


def execute():
	"""Move each event's schedule rows and tracks into a Buzz Schedule of its own."""
	if not frappe.db.table_exists("Schedule Item") or not frappe.db.table_exists("Event Track"):
		return

	for event in events_with_schedules():
		if frappe.db.exists("Buzz Event", event) and not frappe.db.exists("Buzz Schedule", {"event": event}):
			move_schedule(event)


def events_with_schedules() -> set[str]:
	rows = frappe.get_all("Schedule Item", filters={"parenttype": "Buzz Event"}, pluck="parent")
	return set(rows) | set(frappe.get_all("Event Track", pluck="event"))


def move_schedule(event: str):
	rows = frappe.get_all(
		"Schedule Item",
		filters={"parenttype": "Buzz Event", "parent": event},
		fields=["date", "track", "type", "talk", "description", "start_time", "end_time"],
		order_by="date, start_time",
	)
	schedule = frappe.get_doc(
		{
			"doctype": "Buzz Schedule",
			"event": event,
			"is_published": int(bool(rows)),
			"days": days_for(event, rows),
		}
	)
	schedule.flags.ignore_permissions = True
	schedule.insert()

	tracks = move_tracks(event, schedule.name)
	for row in rows:
		schedule.append("items", item_from(row, tracks, event))
	schedule.save()


def days_for(event: str, rows: list) -> str:
	"""The event's own days, plus any date a row used outside them."""
	dates = {getdate(day["date"]) for day in frappe.parse_json(event_days(event))}
	dates |= {getdate(row.date) for row in rows}
	return frappe.as_json(
		[
			{"date": str(date), "label": _("Day {0}").format(index + 1)}
			for index, date in enumerate(sorted(dates))
		]
	)


def move_tracks(event: str, schedule: str) -> dict[str, str]:
	tracks = {}
	for old_name in frappe.get_all("Event Track", filters={"event": event}, pluck="name"):
		track = frappe.get_doc({"doctype": "Buzz Schedule Track", "schedule": schedule, "title": old_name})
		track.flags.ignore_permissions = True
		tracks[old_name] = track.insert().name
	return tracks


def item_from(row, tracks: dict[str, str], event: str) -> dict:
	item = {
		"date": row.date,
		"type": row.type,
		"title": row.description,
		"start_time": row.start_time,
		"end_time": row.end_time,
		"track": tracks.get(row.track),
		"all_tracks": int(not tracks.get(row.track)),
	}
	if not row.talk:
		return item
	talk_event, talk_title = frappe.db.get_value("Event Talk", row.talk, ["event", "title"]) or (None, None)
	# Desk never stopped a row naming another event's talk; keep its title, drop the link.
	if str(talk_event) == str(event):
		item.update(reference_doctype="Event Talk", reference_document=row.talk)
	else:
		item["title"] = item["title"] or talk_title
	return item
