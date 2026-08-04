import frappe

# Frozen list: the doctypes that were team-direct when this patch was written.
TEAM_DIRECT_DOCTYPES = ("Buzz Event", "Event Venue", "Event Host", "Event Template", "Buzz Campaign")


def execute():
	teamless = [doctype for doctype in TEAM_DIRECT_DOCTYPES if has_teamless_rows(doctype)]
	if not teamless:
		return

	team = get_site_default_team()
	for doctype in teamless:
		table = frappe.qb.DocType(doctype)
		frappe.qb.update(table).set(table.team, team).where((table.team.isnull()) | (table.team == "")).run()


def has_teamless_rows(doctype: str) -> bool:
	return bool(frappe.get_all(doctype, filters={"team": ("is", "not set")}, limit=1))


def get_site_default_team() -> str:
	"""The site's first owned team, or a new one when the site has none."""
	owned = frappe.db.get_value(
		"Buzz Team Membership",
		{"team_role": "Owner", "enabled": 1},
		"team",
		order_by="creation asc",
	)
	if owned:
		return owned

	return frappe.get_doc({"doctype": "Buzz Team", "team_name": "Default Team"}).insert().name
