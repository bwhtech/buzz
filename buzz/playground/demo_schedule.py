import frappe

# (type, start time, minutes, track, title); no track spans every track.
ITEMS = (
	("Registration", "10:00:00", 30, None, None),
	("Keynote", "10:30:00", 45, "Main Hall", "Opening keynote"),
	("Coffee break", "11:15:00", 15, None, None),
	("Workshop", "11:30:00", 90, "Workshop Room", "Build a check-in kiosk"),
	("Lunch", "13:00:00", 60, None, None),
)
SCHEDULED_TALK_START = "11:30:00"
SEEDED_SCHEDULED_TALKS = 1


class DemoSchedule:
	"""A draft schedule for the conference: one talk placed, the rest left in the library."""

	def __init__(self, event: str, talks: list[str]):
		self.event = event
		self.talks = talks

	def create(self):
		schedule = frappe.get_doc({"doctype": "Buzz Schedule", "event": self.event})
		schedule.insert(ignore_permissions=True)
		tracks = self.create_tracks(schedule.name)
		date = frappe.db.get_value("Buzz Event", self.event, "start_date")
		for item_type, start_time, minutes, track, title in ITEMS:
			schedule.append(
				"items", self.item(date, item_type, start_time, minutes, tracks.get(track), title)
			)
		talk = self.item(date, "Talk", SCHEDULED_TALK_START, 30, tracks["Main Hall"], None)
		talk.update({"reference_doctype": "Event Talk", "reference_document": self.talks[0]})
		schedule.append("items", talk)
		schedule.save(ignore_permissions=True)

	def create_tracks(self, schedule: str) -> dict[str, str]:
		return {
			title: frappe.get_doc(
				{"doctype": "Buzz Schedule Track", "schedule": schedule, "title": title, "sequence": sequence}
			)
			.insert(ignore_permissions=True)
			.name
			for sequence, title in enumerate(("Main Hall", "Workshop Room"))
		}

	def item(self, date, item_type: str, start_time: str, minutes: int, track: str | None, title) -> dict:
		return {
			"date": date,
			"type": item_type,
			"title": title,
			"start_time": start_time,
			"duration": minutes * 60,
			"all_tracks": not track,
			"track": track,
		}
