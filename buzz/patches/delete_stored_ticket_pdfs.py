import frappe


def execute():
	# Tens of thousands of files on a busy site, so the deletion runs outside the migrate.
	frappe.enqueue(
		"buzz.ticketing.stored_ticket_pdf.delete_stored_ticket_pdfs",
		queue="long",
		timeout=4 * 60 * 60,
		job_id="delete_stored_ticket_pdfs",
		deduplicate=True,
	)
