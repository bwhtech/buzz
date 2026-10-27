import { test, expect, type APIRequestContext } from "@playwright/test"

import { CUSTOM_FORMS_EVENT_ROUTE } from "../data/custom-forms"
import { createDoc, getDoc, getList, updateDoc } from "../helpers/frappe"
import { CustomFormPage } from "../pages"

const FORM_ROUTE = "builder-check"

interface NamedDoc {
	name: string
}

// A form of its own, so renaming its questions never touches what other specs read.
async function builderForm(
	request: APIRequestContext,
	questions: Record<string, string>[] = [
		{ label: "Favourite brew", fieldname: "favourite_brew", fieldtype: "Data" },
	],
): Promise<{ event: string; form: string }> {
	const [event] = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { route: ["=", CUSTOM_FORMS_EVENT_ROUTE] },
	})
	const [existing] = await getList<NamedDoc>(request, "Buzz Form", {
		filters: { event: ["=", event.name], route: ["=", FORM_ROUTE] },
	})
	if (existing) {
		await updateDoc(request, "Buzz Form", existing.name, {
			questions,
			publish: 1,
			logic_rules: null,
		})
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

// custom-forms.setup counts the event's published forms, so this one is closed again after.
test.afterAll(async ({ request }) => {
	const [form] = await getList<NamedDoc>(request, "Buzz Form", {
		filters: { route: ["=", FORM_ROUTE] },
	})
	if (form) await updateDoc(request, "Buzz Form", form.name, { publish: 0 })
})

test("renaming a question in the builder shows on the public form", async ({ page, request }) => {
	const { event, form } = await builderForm(request)

	await page.goto(`/b/manage/events/${event}/forms/${form}`)
	const label = page.getByRole("textbox", { name: "Label of Short text field" })
	await label.fill("Favourite coffee")
	await page.getByRole("button", { name: "Save" }).click()
	await expect(page.getByText("Form saved")).toBeVisible()

	const formPage = new CustomFormPage(page)
	await formPage.goto(CUSTOM_FORMS_EVENT_ROUTE, FORM_ROUTE)
	await formPage.expectFieldVisible("Favourite coffee")
})

test("questions added, dragged and deleted in the builder save in order", async ({
	page,
	request,
}) => {
	const { event, form } = await builderForm(request)
	await page.goto(`/b/manage/events/${event}/forms/${form}`)

	const composer = page.getByRole("combobox", { name: "Add a field" })
	await composer.fill("Roast level")
	await composer.press("Enter")
	await composer.fill("/rati")
	await composer.press("Enter")

	// The rating was added last and is selected; its settings panel deletes it.
	await page.getByRole("button", { name: "Delete" }).click()

	const labels = page.getByRole("textbox", { name: /^Label of/ })
	// Palette items drag too, so rows are the draggables that hold a label input.
	const rows = page.locator('[draggable="true"]').filter({ has: labels })
	await rows.last().dragTo(rows.first(), { targetPosition: { x: 20, y: 4 } })
	await expect(labels.first()).toHaveValue("Roast level")

	await page.getByRole("button", { name: "Save" }).click()
	await expect(page.getByText("Form saved")).toBeVisible()
	const saved = await getDoc<{ questions: { label: string; is_standard: number }[] }>(
		request,
		"Buzz Form",
		form,
	)
	const questions = saved.questions.filter((row) => !row.is_standard).map((row) => row.label)
	expect(questions).toEqual(["Roast level", "Favourite brew"])
})

test("a rule built in the Logic tab shows a question only for the chosen answer", async ({
	page,
	request,
}) => {
	const { event, form } = await builderForm(request, [
		{ label: "Level", fieldname: "level", fieldtype: "Select", options: "Beginner\nAdvanced" },
		{ label: "Outline", fieldname: "outline", fieldtype: "Data" },
	])
	await page.goto(`/b/manage/events/${event}/forms/${form}`)
	await page.getByRole("radio", { name: "Logic" }).click()
	await page.getByRole("button", { name: "New rule" }).click()

	// The rule acts on the last question and opens on the form's first field.
	await page.getByRole("button", { name: "How can we improve?" }).click()
	await page.getByRole("menuitem", { name: "Level" }).click()
	await page.getByRole("button", { name: "Beginner" }).click()
	await page.getByRole("menuitem", { name: "Advanced" }).click()
	await page.getByRole("button", { name: "Save" }).click()
	await expect(page.getByText("Form saved")).toBeVisible()

	const formPage = new CustomFormPage(page)
	await formPage.goto(CUSTOM_FORMS_EVENT_ROUTE, FORM_ROUTE)
	await expect(page.getByText("Outline")).toBeHidden()
	await page.getByRole("combobox", { name: "Level" }).click()
	await page.getByRole("option", { name: "Advanced" }).click()
	await expect(page.getByText("Outline")).toBeVisible()
})

test("settings change the public form's button and confirmation", async ({ page, request }) => {
	const { event, form } = await builderForm(request)
	await updateDoc(request, "Buzz Form", form, { submit_label: null, success_title: null })
	await page.goto(`/b/manage/events/${event}/forms/${form}`)
	await page.getByRole("radio", { name: "Settings" }).click()
	await page.getByLabel("Button label").fill("Send it")
	await page.getByLabel("Confirmation title").fill("Got it, thanks")
	await page.getByRole("button", { name: "Save" }).click()
	await expect(page.getByText("Form saved")).toBeVisible()

	const formPage = new CustomFormPage(page)
	await formPage.goto(CUSTOM_FORMS_EVENT_ROUTE, FORM_ROUTE)
	await page.getByRole("button", { name: "Send it" }).click()
	await expect(page.getByText("Got it, thanks")).toBeVisible()
})

test("registration edits attendee and booking questions, with ticket-type chips", async ({
	page,
	request,
}) => {
	const [event] = await getList<NamedDoc>(request, "Buzz Event", {
		filters: { route: ["=", CUSTOM_FORMS_EVENT_ROUTE] },
	})
	const [form] = await getList<NamedDoc>(request, "Buzz Form", {
		filters: { event: ["=", event.name], form_doctype: ["=", "Event Booking"] },
	})
	const [ticketType] = await getList<NamedDoc & { title: string }>(request, "Event Ticket Type", {
		filters: { event: ["=", event.name] },
		fields: ["name", "title"],
	})
	await page.goto(`/b/manage/events/${event.name}/forms/${form.name}`)

	await expect(page.getByText("Always asked:")).toContainText("First name")
	const composer = page.getByRole("combobox", { name: "Add a field" })
	await composer.fill("Seat preference")
	await composer.press("Enter")
	await page.getByRole("button", { name: ticketType.title, exact: true }).click()
	await expect(page.getByRole("button", { name: "All tickets" })).not.toHaveClass(/solid/)

	await page.getByRole("radio", { name: "Logic" }).click()
	await expect(page.getByRole("button", { name: "Seat preference" })).toBeVisible()

	await page.getByRole("radio", { name: "Build" }).click()
	await page.getByRole("radio", { name: "Booking · once" }).click()
	await expect(page.getByText("Always asked:")).not.toContainText("First name")
	// Nothing is saved: other specs read this event's registration questions.
})

test.describe("on a phone", () => {
	test.use({ viewport: { width: 390, height: 844 } })

	test("fields are added from a sheet and their settings open from the row menu", async ({
		page,
		request,
	}) => {
		const { event, form } = await builderForm(request)
		await page.goto(`/b/manage/events/${event}/forms/${form}`)

		await page.getByRole("button", { name: "Add a field" }).click()
		await page.getByRole("dialog").getByRole("button", { name: "Email" }).click()
		await expect(page.getByRole("textbox", { name: "Label of Email field" })).toBeVisible()

		const row = page
			.locator('[draggable="true"]')
			.filter({ has: page.getByRole("textbox", { name: "Label of Email field" }) })
		await row.getByRole("button", { name: "More actions" }).click()
		await page.getByRole("menuitem", { name: "Field settings" }).click()
		await expect(page.getByRole("dialog").getByText("Placeholder")).toBeVisible()
	})
})
