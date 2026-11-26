import frappe


def execute():
	index_definitions = [
		("Sponsorship Enquiry", ["event", "creation", "name"], "sponsorship_enquiry_event_creation_idx"),
		("Sponsorship Enquiry", ["owner"], None),
		("Event Talk", ["event"], None),
		("Event Talk", ["proposal"], None),
		("Sponsorship Tier", ["event"], None),
		("Talk Proposal", ["event", "creation", "name"], "talk_proposal_event_creation_idx"),
		("Talk Proposal", ["submitted_by"], None),
		("Proposal Speaker", ["parenttype", "email"], None),
		("Event Sponsor", ["enquiry"], None),
		("Event Sponsor", ["event", "creation", "name"], "event_sponsor_event_creation_idx"),
		("Community Event Request", ["community", "status", "event"], "cer_community_status_event_idx"),
		(
			"Community Event Request",
			["community", "status", "is_external_event"],
			"cer_community_status_external_idx",
		),
		("Buzz Team Membership", ["team", "enabled", "team_role"], "btm_team_enabled_role_idx"),
		("Buzz Team Membership", ["user", "enabled", "team_role"], "btm_user_enabled_role_idx"),
		("Buzz Event Collaborator", ["user", "status"], None),
		("Buzz Event Collaborator", ["invite_key_hash"], None),
		("Buzz Event Collaborator", ["event", "email"], None),
		("Buzz Team", ["accept_community_submissions", "is_published"], "buzz_team_open_community_idx"),
		("Buzz Event", ["team", "is_published", "end_date", "start_date"], "buzz_event_team_pub_dates_idx"),
		(
			"Buzz Notification Subscription",
			["reference_doctype", "reference_name", "user"],
			"bns_ref_user_idx",
		),
		("Ticket Cancellation Request", ["booking", "docstatus"], None),
		("Notification Log", ["for_user", "type", "creation"], "notif_log_user_type_creation_idx"),
	]
	for doctype, fields, index_name in index_definitions:
		frappe.db.add_index(doctype, fields, index_name=index_name)

	existing = frappe.db.sql(
		"SHOW INDEX FROM `tabNotification Log` WHERE Key_name = %s", ("notif_log_user_type_read_idx",)
	)
	if not existing:
		frappe.db.sql_ddl(
			"ALTER TABLE `tabNotification Log` ADD INDEX `notif_log_user_type_read_idx` (`for_user`, `type`, `read`)"
		)
