import frappe

from buzz.api.schedule import services
from buzz.api.schedule.schemas import ScheduleTalk


@frappe.whitelist(methods=["POST"])
def get_or_create_schedule(event: int) -> str:
	"""The event's schedule, made with a first track when it has none yet."""
	return services.get_or_create_schedule(event)


@frappe.whitelist()
def get_schedule_talks(event: int) -> list[ScheduleTalk]:
	"""Accepted talks of the event, with their speakers, for the library."""
	return services.event_talks(event)
