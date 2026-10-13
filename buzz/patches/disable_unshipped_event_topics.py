import frappe

SHIPPED_TOPICS = (
	"AI",
	"Art & Culture",
	"Community",
	"Design",
	"Education",
	"Open Source",
	"Startups",
	"Tech",
)


def execute():
	"""Disable standard topics dropped from the shipped set; events keep their links to them."""
	topic = frappe.qb.DocType("Event Topic")
	frappe.qb.update(topic).set(topic.enabled, 0).set(topic.is_published, 0).where(
		(topic.is_standard == 1) & topic.name.notin(SHIPPED_TOPICS)
	).run()
