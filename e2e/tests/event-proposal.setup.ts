import { test as setup } from "@playwright/test"

import { createDoc, docExists, updateDoc } from "../helpers/frappe"

const testCategoryName = "E2E Test Category"

setup("setup event proposal form", async ({ request }) => {
	if (!(await docExists(request, "Event Category", testCategoryName))) {
		await createDoc(request, "Event Category", {
			name: testCategoryName,
			enabled: 1,
			slug: "e2e-test-category",
		})
		console.log(`Created Event Category: ${testCategoryName}`)
	}

	await updateDoc(request, "Buzz Settings", "Buzz Settings", {
		accept_event_proposals: 1,
		allow_guest_event_proposals: 1,
	})

	console.log("Event proposal form enabled in Buzz Settings")
})
