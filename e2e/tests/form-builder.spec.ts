import { test, expect, type APIRequestContext } from "@playwright/test"

import { CUSTOM_FORMS_EVENT_ROUTE } from "../data/custom-forms"
import { createDoc, getList, updateDoc } from "../helpers/frappe"
import { CustomFormPage } from "../pages"

const FORM_ROUTE = "builder-check"

interface NamedDoc {
	name: string
}

// A form of its own, so renaming its questions never touches what other specs read.
async function builderForm(request: APIRequestContext): Promise<{ event: string; form: string }> {
	const [event] = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { route: ["=", CUSTOM_FORMS_EVENT_ROUTE] },
	})
	const questions = [{ label: "Favourite brew", fieldname: "favourite_brew", fieldtype: "Data" }]
	const [existing] = await getList<NamedDoc>(request, "Buzz Form", {
		filters: { event: ["=", event.name], route: ["=", FORM_ROUTE] },
	})
	if (existing) {
		await updateDoc(request, "Buzz Form", existing.name, { questions })
		return { event: event.name, form: existing.name }
	}
	const form = await createDoc<NamedDoc>(request, "Buzz Form", {
		title: "Builder check",
		event: event.name,
		form_doctype: "Event Feedback",
		route: FORM_ROUTE,
		publish: 1,
		questions,
	})
	return { event: event.name, form: form.name }
}

test("renaming a question in the builder shows on the public form", async ({ page, request }) => {
	const { event, form } = await builderForm(request)

	await page.goto(`/b/manage/events/${event}/forms/${form}`)
	const label = page.getByRole("textbox", { name: "Label of Short text field" })
	await label.fill("Favourite coffee")
	await page.getByRole("button", { name: "Save" }).click()
	await expect(page.getByRole("button", { name: "Save" })).toBeDisabled()

	const formPage = new CustomFormPage(page)
	await formPage.goto(CUSTOM_FORMS_EVENT_ROUTE, FORM_ROUTE)
	await formPage.expectFieldVisible("Favourite coffee")
})
