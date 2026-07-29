import frappe

from buzz.payments import get_payment_link_for_sponsorship


@frappe.whitelist()
def get_sponsorship_details(enquiry_id: str) -> dict:
	enquiry = frappe.get_doc("Sponsorship Enquiry", enquiry_id)

	if enquiry.owner != frappe.session.user and not frappe.has_permission(
		"Sponsorship Enquiry", "read", enquiry
	):
		frappe.throw(frappe._("Not permitted to view this sponsorship enquiry"))

	tier_title = ""
	if enquiry.tier:
		tier_title = frappe.db.get_value("Sponsorship Tier", enquiry.tier, "title") or enquiry.tier

	event_details = {}
	if enquiry.event:
		event = frappe.get_cached_doc("Buzz Event", enquiry.event)
		event_details = {
			"title": event.title,
			"short_description": getattr(event, "short_description", ""),
			"about": getattr(event, "about", ""),
			"start_date": event.start_date,
			"end_date": getattr(event, "end_date", ""),
			"venue": getattr(event, "venue", ""),
			"route": getattr(event, "route", ""),
		}

	sponsor_details = None
	sponsors = frappe.db.get_all(
		"Event Sponsor",
		filters={"enquiry": enquiry_id},
		fields=["name", "company_name", "company_logo", "creation", "event", "tier"],
		limit=1,
	)

	if sponsors:
		sponsor_details = sponsors[0]
		if sponsor_details.get("tier"):
			sponsor_tier_title = frappe.db.get_value("Sponsorship Tier", sponsor_details["tier"], "title")
			sponsor_details["tier_title"] = sponsor_tier_title or sponsor_details["tier"]

	return {
		"enquiry": {
			"name": enquiry.name,
			"company_name": enquiry.company_name,
			"company_logo": enquiry.company_logo,
			"event": enquiry.event,
			"tier": enquiry.tier,
			"tier_title": tier_title,
			"status": enquiry.status,
			"creation": enquiry.creation,
			"owner": enquiry.owner,
		},
		"event_details": event_details,
		"sponsor_details": sponsor_details,
		"has_sponsor": bool(sponsor_details),
	}


@frappe.whitelist()
def get_user_sponsorship_inquiries() -> list:
	inquiries = frappe.db.get_all(
		"Sponsorship Enquiry",
		filters={"owner": frappe.session.user},
		fields=["name", "company_name", "event", "tier", "status", "creation"],
		order_by="creation desc",
	)

	for inquiry in inquiries:
		if inquiry.event:
			event_title = frappe.db.get_value("Buzz Event", inquiry.event, "title")
			inquiry["event_title"] = event_title

		if inquiry.tier:
			tier_title = frappe.db.get_value("Sponsorship Tier", inquiry.tier, "title")
			inquiry["tier_title"] = tier_title or inquiry.tier
		else:
			inquiry["tier_title"] = ""

	inquiry_names = [inquiry.name for inquiry in inquiries]
	if inquiry_names:
		sponsors = frappe.db.get_all(
			"Event Sponsor",
			filters={"enquiry": ["in", inquiry_names]},
			fields=["enquiry"],
		)
		sponsored_inquiries = {sponsor.enquiry for sponsor in sponsors}

		for inquiry in inquiries:
			inquiry["has_sponsor"] = inquiry.name in sponsored_inquiries
	else:
		for inquiry in inquiries:
			inquiry["has_sponsor"] = False

	return inquiries


@frappe.whitelist()
def create_sponsorship_payment_link(enquiry_id: str, tier_id: str, payment_gateway: str | None = None) -> str:
	enquiry = frappe.get_doc("Sponsorship Enquiry", enquiry_id)
	if enquiry.owner != frappe.session.user:
		frappe.throw(frappe._("Not permitted to create payment for this enquiry"))

	redirect_url = f"/b/account/sponsorships/{enquiry_id}?success=true"
	return get_payment_link_for_sponsorship(
		enquiry_id, tier_id, redirect_url, payment_gateway=payment_gateway
	)


@frappe.whitelist()
def withdraw_sponsorship_enquiry(enquiry_id: str):
	enquiry = frappe.get_cached_doc("Sponsorship Enquiry", enquiry_id)
	if enquiry.owner != frappe.session.user:
		frappe.throw(frappe._("Not permitted to withdraw this enquiry"))

	if enquiry.status == "Paid":
		frappe.throw(frappe._("Cannot withdraw a paid sponsorship enquiry"))

	if enquiry.status == "Withdrawn":
		frappe.throw(frappe._("This sponsorship enquiry has already been withdrawn"))

	enquiry.status = "Withdrawn"
	enquiry.save(ignore_permissions=True)
