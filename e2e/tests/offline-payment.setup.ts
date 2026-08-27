import { test as setup } from "@playwright/test"

import { callMethod, createDoc, docExists, getList } from "../helpers/frappe"

interface NamedDoc {
	name: string
}

const testCategoryName = "E2E Test Category"
const testHostName = "E2E Test Host"

const offlinePaymentEvent = {
	title: "E2E Offline Payment",
	route: "offline-payment-e2e",
}

async function forceCleanup(
	request: Parameters<typeof callMethod>[0],
	doctype: string,
	name: string,
): Promise<void> {
	try {
		await callMethod(request, "frappe.client.cancel", { doctype, name })
	} catch {
		// Not submittable or already cancelled
	}
	await callMethod(request, "frappe.client.delete", { doctype, name })
}

setup("create offline payment test event", async ({ request }) => {
	// Clean up existing test event - retry if needed
	for (let attempt = 0; attempt < 2; attempt++) {
		try {
			const events = await getList<NamedDoc>(request, "Buzz Event", {
				filters: { route: offlinePaymentEvent.route },
			})

			if (events.length === 0) break

			for (const existing of events) {
				const linkedDoctypes = [
					{ doctype: "Event Ticket", submittable: true },
					{ doctype: "Event Booking", submittable: true },
					{ doctype: "Sponsorship Tier", submittable: false },
					{ doctype: "Event Ticket Type", submittable: false },
					{ doctype: "Ticket Add-on", submittable: false },
					{ doctype: "Offline Payment Method", submittable: false },
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

				await callMethod(request, "frappe.client.delete", {
					doctype: "Buzz Event",
					name: existing.name,
				}).catch((e) => console.log(`Failed to delete event: ${e}`))
			}
		} catch (error) {
			console.log(`Cleanup attempt ${attempt + 1}: ${error}`)
		}
	}

	// Ensure category and host exist
	if (!(await docExists(request, "Event Category", testCategoryName))) {
		await createDoc(request, "Event Category", {
			name: testCategoryName,
			enabled: 1,
			slug: "e2e-test-category",
		})
	}

	if (!(await docExists(request, "Event Host", testHostName))) {
		await createDoc(request, "Event Host", {
			name: testHostName,
		})
	}

	const futureDate = new Date()
	futureDate.setMonth(futureDate.getMonth() + 1)
	const startDate = futureDate.toISOString().split("T")[0]

	// Create event
	const event = await createDoc<NamedDoc>(request, "Buzz Event", {
		title: offlinePaymentEvent.title,
		category: testCategoryName,
		host: testHostName,
		start_date: startDate,
		start_time: "09:00:00",
		end_time: "17:00:00",
		route: offlinePaymentEvent.route,
		is_published: 1,
		medium: "In Person",
	})

	// Create offline payment method
	await createDoc<NamedDoc>(request, "Offline Payment Method", {
		event: event.name,
		title: "Bank Transfer",
		enabled: 1,
		description: "<p>Transfer to Account: 123456789</p>",
	})

	// Create paid ticket type
	await createDoc<NamedDoc>(request, "Event Ticket Type", {
		event: event.name,
		title: "Standard Ticket",
		price: 500,
		currency: "INR",
		is_published: 1,
	})

	console.log(`Created: ${offlinePaymentEvent.title} (route: ${offlinePaymentEvent.route})`)
	console.log("Offline payment event setup complete!")
})
