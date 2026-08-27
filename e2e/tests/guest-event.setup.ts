import { test as setup } from "@playwright/test"

import { callMethod, createDoc, docExists, ensureTestTeam, getList } from "../helpers/frappe"

interface NamedDoc {
	name: string
}

const testCategoryName = "E2E Test Category"
const testHostName = "E2E Test Host"

const guestEvents = [
	{
		title: "E2E Guest No OTP",
		route: "guest-no-otp-e2e",
		guest_verification_method: "None",
	},
	{
		title: "E2E Guest Email OTP",
		route: "guest-email-otp-e2e",
		guest_verification_method: "Email OTP",
	},
	{
		title: "E2E Guest Phone OTP",
		route: "guest-phone-otp-e2e",
		guest_verification_method: "Phone OTP",
	},
]

/**
 * Cancel and delete a document. Submittable docs (Event Booking, Event Ticket)
 * must be cancelled (docstatus=2) before they can be deleted.
 */
async function forceCleanup(
	request: Parameters<typeof callMethod>[0],
	doctype: string,
	name: string,
): Promise<void> {
	try {
		await callMethod(request, "frappe.client.cancel", { doctype, name })
	} catch {
		// Not submittable or already cancelled — ignore
	}
	await callMethod(request, "frappe.client.delete", { doctype, name })
}

setup("create guest booking test events", async ({ request }) => {
	// Clean up existing guest test events by route (unique constraint).
	// Must delete in order: tickets → bookings → ticket types → events
	// because Frappe blocks deletion of documents with linked records.
	for (const evt of guestEvents) {
		try {
			const events = await getList<NamedDoc>(request, "Buzz Event", {
				filters: { route: evt.route },
			})
			if (!events.length) continue

			for (const existing of events) {
				// Delete all linked docs in dependency order.
				// Tickets and bookings are submittable (cancel before delete).
				const linkedDoctypes = [
					{ doctype: "Event Ticket", submittable: true },
					{ doctype: "Event Booking", submittable: true },
					{ doctype: "Sponsorship Tier", submittable: false },
					{ doctype: "Event Ticket Type", submittable: false },
					{ doctype: "Ticket Add-on", submittable: false },
				]

				for (const { doctype, submittable } of linkedDoctypes) {
					const docs = await getList<NamedDoc>(request, doctype, {
						filters: { event: existing.name },
					}).catch(() => [] as NamedDoc[])

					for (const doc of docs) {
						if (submittable) {
							await forceCleanup(request, doctype, doc.name).catch(() => {})
						} else {
							await callMethod(request, "frappe.client.delete", {
								doctype,
								name: doc.name,
							}).catch(() => {})
						}
					}
				}

				// Delete the event itself
				await callMethod(request, "frappe.client.delete", {
					doctype: "Buzz Event",
					name: existing.name,
				}).catch((e) => console.log(`Cleanup event ${existing.name}: ${e}`))
			}
		} catch (error) {
			const message = error instanceof Error ? error.message : String(error)
			console.log(`Cleanup: ${evt.title} - ${message}`)
		}
	}

	// Ensure category and host exist (shared with event.setup.ts)
	if (!(await docExists(request, "Event Category", testCategoryName))) {
		await createDoc(request, "Event Category", {
			name: testCategoryName,
			enabled: 1,
			slug: "e2e-test-category",
		})
	}

	const team = await ensureTestTeam(request)

	if (!(await docExists(request, "Event Host", testHostName))) {
		await createDoc(request, "Event Host", {
			name: testHostName,
			team,
		})
	}

	const futureDate = new Date()
	futureDate.setMonth(futureDate.getMonth() + 1)
	const startDate = futureDate.toISOString().split("T")[0]

	// Create each guest test event with a free ticket type
	for (const evt of guestEvents) {
		const event = await createDoc<NamedDoc>(request, "Buzz Event", {
			team,
			title: evt.title,
			category: testCategoryName,
			host: testHostName,
			start_date: startDate,
			start_time: "09:00:00",
			end_time: "17:00:00",
			route: evt.route,
			is_published: 1,
			medium: "In Person",
			allow_guest_booking: 1,
			guest_verification_method: evt.guest_verification_method,
		})

		await createDoc<NamedDoc>(request, "Event Ticket Type", {
			event: event.name,
			title: "Free Ticket",
			price: 0,
			currency: "INR",
			is_published: 1,
		})

		console.log(
			`Created: ${evt.title} (route: ${evt.route}, method: ${evt.guest_verification_method})`,
		)
	}

	console.log("Guest event setup complete!")
})
