import frappe


def execute():
	"""Carry a legacy `Buzz Event.host` into the co-host table so it stays on display.

	Hosts auto-minted per team are skipped: their `host_name` is the team's own name, so a
	row would list the team twice under "Hosted by".
	"""
	event = frappe.qb.DocType("Buzz Event")
	host = frappe.qb.DocType("Event Host")
	team = frappe.qb.DocType("Buzz Team")

	rows = (
		frappe.qb.from_(event)
		.join(host)
		.on(host.name == event.host)
		.left_join(team)
		.on(team.name == event.team)
		.select(event.name.as_("event"), event.host)
		.where(host.host_name != team.team_name)
	).run(as_dict=True)

	co_host = frappe.qb.DocType("Event CoHost")
	already = set(
		(frappe.qb.from_(co_host).select(co_host.parent).where(co_host.parenttype == "Buzz Event")).run(
			pluck=True
		)
	)

	for row in rows:
		if str(row.event) in already:
			continue
		frappe.get_doc(
			{
				"doctype": "Event CoHost",
				"parenttype": "Buzz Event",
				"parentfield": "co_hosts",
				"parent": row.event,
				"host": row.host,
				"idx": 1,
			}
		).db_insert()
