import json

import frappe


def execute():
	"""Disable standard topics dropped from the shipped set; events keep their links to them."""
	with open(frappe.get_app_path("buzz", "fixtures", "event_topic.json")) as fixture:
		shipped = [row["name"] for row in json.load(fixture)]
	topic = frappe.qb.DocType("Event Topic")
	frappe.qb.update(topic).set(topic.enabled, 0).set(topic.is_published, 0).where(
		(topic.is_standard == 1) & topic.name.notin(shipped)
	).run()
