import frappe

STATUSES = [
	{"name": "Review Pending", "color": "Orange"},
	{"name": "Shortlisted", "color": "Blue"},
	{"name": "Accepted", "color": "Green"},
	{"name": "Rejected", "color": "Red"},
	{"name": "Replied", "color": "Purple"},
	{"name": "Duplicate", "color": "Gray"},
]


def execute():
	for status in STATUSES:
		if frappe.db.exists("Talk Proposal Status", status["name"]):
			continue

		doc = frappe.new_doc("Talk Proposal Status")
		doc.name = status["name"]
		doc.color = status["color"]
		doc.insert(ignore_permissions=True)
