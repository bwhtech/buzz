import { test as setup, expect } from "@playwright/test"

import {
	CLOSED_FORM_MESSAGE,
	CLOSED_FORM_ROUTE,
	CLOSED_FORM_TITLE,
	CUSTOM_FORMS_EVENT_ROUTE,
	MEMBERS_ONLY_FORM_ROUTE,
} from "../data/custom-forms"
import { createDoc, docExists, ensureTestTeam, getDoc, getList, updateDoc } from "../helpers/frappe"

interface NamedDoc {
	name: string
}

const testCategoryName = "E2E Test Category"
const testHostName = "E2E Test Host"

setup("setup custom forms on test event", async ({ request }) => {
	let eventName: string

	const events = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { route: ["=", CUSTOM_FORMS_EVENT_ROUTE] },
	})

	if (events.length > 0) {
		eventName = events[0].name
	} else {
		if (!(await docExists(request, "Event Category", testCategoryName))) {
			await createDoc(request, "Event Category", {
				name: testCategoryName,
				enabled: 1,
				slug: "e2e-test-category",
			})
		}
		const team = await ensureTestTeam(request)

		if (!(await docExists(request, "Event Host", testHostName))) {
			await createDoc(request, "Event Host", { name: testHostName, team })
		}

		const futureDate = new Date()
		futureDate.setMonth(futureDate.getMonth() + 1)
		const startDate = futureDate.toISOString().split("T")[0]

		const event = await createDoc<NamedDoc>(request, "Buzz Event", {
			team,
			title: "E2E Custom Forms Event",
			category: testCategoryName,
			host: testHostName,
			start_date: startDate,
			route: CUSTOM_FORMS_EVENT_ROUTE,
			is_published: 1,
			start_time: "09:00:00",
			end_time: "17:00:00",
			medium: "In Person",
		})
		eventName = event.name
	}

	await updateDoc(request, "Buzz Event", eventName, {
		custom_forms: [
			{ doctype: "Buzz Event Form", form_doctype: "Event Feedback", route: "feedback", publish: 1 },
			{
				doctype: "Buzz Event Form",
				form_doctype: "Talk Proposal",
				route: "propose-talk",
				publish: 1,
			},
			{
				doctype: "Buzz Event Form",
				form_doctype: "Sponsorship Enquiry",
				route: "enquire-sponsorship",
				publish: 1,
			},
			{
				doctype: "Buzz Event Form",
				form_doctype: "Event Feedback",
				route: MEMBERS_ONLY_FORM_ROUTE,
				publish: 1,
				login_required: 1,
			},
			{
				doctype: "Buzz Event Form",
				form_doctype: "Event Feedback",
				route: CLOSED_FORM_ROUTE,
				publish: 1,
				auto_close_at: "2020-01-01 00:00:00",
				closed_title: CLOSED_FORM_TITLE,
				closed_message: CLOSED_FORM_MESSAGE,
			},
		],
	})

	const updated = await getDoc<{ custom_forms: Array<{ route: string; publish: number }> }>(
		request,
		"Buzz Event",
		eventName,
	)
	const publishedForms = (updated.custom_forms || []).filter((f) => f.publish)
	expect(publishedForms.length).toBe(5)

	console.log(
		`Custom forms enabled on event: ${eventName} (${publishedForms.length} forms: ${publishedForms.map((f) => f.route).join(", ")})`,
	)
})
