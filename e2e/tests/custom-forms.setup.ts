import { test as setup, expect, type APIRequestContext } from "@playwright/test"

import {
	CLOSED_FORM_MESSAGE,
	CLOSED_FORM_ROUTE,
	CLOSED_FORM_TITLE,
	CUSTOM_FORMS_EVENT_ROUTE,
	MEMBERS_ONLY_FORM_ROUTE,
} from "../data/custom-forms"
import {
	createDoc,
	docExists,
	ensureEventHost,
	ensureTestTeam,
	getList,
	updateDoc,
} from "../helpers/frappe"

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

		const host = await ensureEventHost(request, testHostName, team)

		const futureDate = new Date()
		futureDate.setMonth(futureDate.getMonth() + 1)
		const startDate = futureDate.toISOString().split("T")[0]

		const event = await createDoc<NamedDoc>(request, "Buzz Event", {
			team,
			title: "E2E Custom Forms Event",
			category: testCategoryName,
			host,
			start_date: startDate,
			route: CUSTOM_FORMS_EVENT_ROUTE,
			is_published: 1,
			start_time: "09:00:00",
			end_time: "17:00:00",
			medium: "In Person",
		})
		eventName = event.name
	}

	const forms = [
		{ form_doctype: "Event Feedback", route: "feedback", publish: 1 },
		{ form_doctype: "Talk Proposal", route: "propose-talk", publish: 1 },
		{
			form_doctype: "Event Feedback",
			route: MEMBERS_ONLY_FORM_ROUTE,
			publish: 1,
			login_required: 1,
		},
		{
			form_doctype: "Event Feedback",
			route: CLOSED_FORM_ROUTE,
			publish: 1,
			auto_close_at: "2020-01-01 00:00:00",
			closed_title: CLOSED_FORM_TITLE,
			closed_message: CLOSED_FORM_MESSAGE,
		},
		{ form_doctype: "Sponsorship Enquiry", route: "enquire-sponsorship", publish: 1 },
	]
	for (const form of forms) {
		await ensureForm(request, eventName, form)
	}

	const publishedForms = await getList<NamedDoc>(request, "Buzz Form", {
		// The registration form stays published and closes by cutoff instead.
		filters: { event: ["=", eventName], publish: ["=", 1], form_doctype: ["!=", "Event Booking"] },
	})
	expect(publishedForms.length).toBe(forms.length)

	console.log(
		`Custom forms enabled on event: ${eventName} (${publishedForms.length} forms: ${forms.map((form) => form.route).join(", ")})`,
	)
})

interface FormInput {
	form_doctype: string
	route: string
	publish: number
	login_required?: number
	auto_close_at?: string
	closed_title?: string
	closed_message?: string
}

async function ensureForm(
	request: APIRequestContext,
	eventName: string,
	form: FormInput,
): Promise<void> {
	const forms = await getList<NamedDoc>(request, "Buzz Form", {
		filters: { event: ["=", eventName], route: ["=", form.route] },
	})
	if (forms.length > 0) {
		await updateDoc(request, "Buzz Form", forms[0].name, form)
		return
	}
	await createDoc(request, "Buzz Form", { event: eventName, title: form.form_doctype, ...form })
}
