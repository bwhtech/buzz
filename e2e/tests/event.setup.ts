import { test as setup, expect } from "@playwright/test";
import { createDoc, deleteDoc, docExists, getList } from "../helpers/frappe";

interface NamedDoc {
	name: string;
}

//  Setup: Creates Event Category, Event Host, Buzz Event, Event Ticket Type, and Ticket Add-on.
setup("create test event for booking", async ({ request }) => {
	const testEventTitle = "E2E Test Event";
	const testEventRoute = "test-event-e2e";
	const testCategoryName = "E2E Test Category";
	const testHostName = "E2E Test Host";

	// Clean up any existing test data first
	try {
		// Find the event by title
		const events = await getList<NamedDoc>(request, "Buzz Event", {
			filters: { title: ["=", testEventTitle] },
		});
		const existingEvent = events[0]; // getList returns array

		if (existingEvent) {
			// Delete sponsorship tiers first
			const tiers = await getList<NamedDoc>(request, "Sponsorship Tier", {
				filters: { event: ["=", existingEvent.name] },
			});
			for (const tier of tiers) {
				await deleteDoc(request, "Sponsorship Tier", tier.name).catch(() => {});
			}

			// Delete ticket types
			const ticketTypes = await getList<NamedDoc>(request, "Event Ticket Type", {
				filters: { event: ["=", existingEvent.name] },
			});
			for (const tt of ticketTypes) {
				await deleteDoc(request, "Event Ticket Type", tt.name).catch(() => {});
			}

			// Delete add-ons
			const addOns = await getList<NamedDoc>(request, "Ticket Add-on", {
				filters: { event: ["=", existingEvent.name] },
			});
			for (const ao of addOns) {
				await deleteDoc(request, "Ticket Add-on", ao.name).catch(() => {});
			}

			// Now delete the event
			await deleteDoc(request, "Buzz Event", existingEvent.name).catch(() => {});
		}
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		console.log("Cleanup: Some test data may not have existed", message);
	}

	// Create Event Category if it doesn't exist
	if (!(await docExists(request, "Event Category", testCategoryName))) {
		await createDoc(request, "Event Category", {
			name: testCategoryName,
			enabled: 1,
			slug: "e2e-test-category",
		});
		console.log(`Created Event Category: ${testCategoryName}`);
	}

	// Create Event Host if it doesn't exist
	if (!(await docExists(request, "Event Host", testHostName))) {
		await createDoc(request, "Event Host", {
			name: testHostName,
		});
		console.log(`Created Event Host: ${testHostName}`);
	}

	// Create Buzz Event
	const futureDate = new Date();
	futureDate.setMonth(futureDate.getMonth() + 1);
	const startDate = futureDate.toISOString().split("T")[0];

	const event = await createDoc<NamedDoc>(request, "Buzz Event", {
		title: testEventTitle,
		category: testCategoryName,
		host: testHostName,
		start_date: startDate,
		route: testEventRoute,
		is_published: 1,
		start_time: "09:00:00",
		end_time: "17:00:00",
		medium: "In Person",
	});
	console.log(`Created Buzz Event: ${event.name} (route: ${testEventRoute})`);

	// Create Event Ticket Type
	const ticketType = await createDoc<NamedDoc>(request, "Event Ticket Type", {
		event: event.name,
		title: "Standard Ticket",
		price: 500,
		currency: "INR",
		is_published: 1,
	});
	console.log(`Created Event Ticket Type: ${ticketType.name}`);

	// Create Ticket Add-on
	const addOn = await createDoc<NamedDoc>(request, "Ticket Add-on", {
		event: event.name,
		title: "Event T-Shirt",
		price: 200,
		currency: "INR",
		enabled: 1,
	});
	console.log(`Created Ticket Add-on: ${addOn.name}`);

	console.log(`Test event setup complete! Route: /b/register/${testEventRoute}`);
});
