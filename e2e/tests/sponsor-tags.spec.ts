import { type Page, expect, test } from "@playwright/test"

import {
	callMethod,
	createDoc,
	deleteDoc,
	ensureEventHost,
	ensureTestTeam,
	getList,
} from "../helpers/frappe"

interface NamedDoc {
	name: string
}

const sponsorCard = (page: Page, company: string) =>
	page.getByRole("button", { name: new RegExp(`^${company}`) })

// Runs under the shared Administrator state. Seeds its own event, so its sponsors and the
// team's tags never meet another spec's; labels carry the run's timestamp for the same reason.
test.describe("Sponsor tags", () => {
	const run = Date.now()
	const seededLabel = `Returning ${run}`
	const createdLabel = `Follow up ${run}`
	let event: string

	test.beforeAll(async ({ request }) => {
		const team = await ensureTestTeam(request)
		event = (
			await createDoc<NamedDoc>(request, "Buzz Event", {
				team,
				title: `Sponsor Tags ${run}`,
				category: "E2E Test Category",
				host: await ensureEventHost(request, "E2E Test Host", team),
				start_date: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
				start_time: "09:00:00",
				end_time: "17:00:00",
				medium: "In Person",
			})
		).name
		const tier = await createDoc<NamedDoc>(request, "Sponsorship Tier", {
			event,
			title: "Gold",
			prices: [{ currency: "INR", price: 50000 }],
		})
		const addSponsor = (company_name: string) =>
			createDoc<NamedDoc>(request, "Event Sponsor", {
				event,
				tier: tier.name,
				company_name,
				company_logo: "/assets/buzz/images/buzz-logo.png",
			})
		await addSponsor("Acme")
		const globex = await addSponsor("Globex")
		const tag = await callMethod<NamedDoc>(request, "buzz.api.tags.create_tag", {
			team,
			document_type: "Event Sponsor",
			label: seededLabel,
		})
		await callMethod(request, "buzz.api.tags.set_tags", {
			document_type: "Event Sponsor",
			document_name: globex.name,
			tags: [tag.name],
		})
	})

	test.afterAll(async ({ request }) => {
		const filters = { event }
		for (const doctype of ["Event Sponsor", "Sponsorship Tier"]) {
			for (const doc of await getList<NamedDoc>(request, doctype, { filters })) {
				await deleteDoc(request, doctype, doc.name).catch(() => {})
			}
		}
		const tags = await getList<NamedDoc>(request, "Buzz Tag", {
			filters: { label: ["in", [seededLabel, createdLabel]] },
		})
		for (const tag of tags) await deleteDoc(request, "Buzz Tag", tag.name).catch(() => {})
		await deleteDoc(request, "Buzz Event", event).catch(() => {})
	})

	test("creates a tag from the drawer and shows it on the card", async ({ page }) => {
		await page.goto(`/b/manage/events/${event}/sponsorships`)
		await sponsorCard(page, "Acme").click()

		const drawer = page.getByRole("dialog")
		await drawer.getByRole("button", { name: "Add tag" }).click()
		await page.getByPlaceholder("Search or create tag").fill(createdLabel)
		await page.keyboard.press("Enter")
		await page.getByRole("option", { name: "Green" }).click()

		await expect(drawer.getByRole("group", { name: "Tags" })).toContainText(createdLabel)
		await page.keyboard.press("Escape")
		await page.keyboard.press("Escape")
		await expect(sponsorCard(page, "Acme").getByLabel(`Tags: ${createdLabel}`)).toBeVisible()
	})

	test("filters the sponsor list by tag", async ({ page }) => {
		await page.goto(`/b/manage/events/${event}/sponsorships`)
		await expect(sponsorCard(page, "Acme")).toBeVisible()

		// The enquiries section has its own Filter button.
		const sponsorsSection = page.getByRole("region", { name: "Sponsors" })
		await sponsorsSection.getByRole("button", { name: "Filter" }).click()
		await page.getByRole("menuitem", { name: "Tags" }).hover()
		await page.getByRole("menuitem", { name: seededLabel }).click()

		await expect(sponsorCard(page, "Globex")).toBeVisible()
		await expect(sponsorCard(page, "Acme")).toHaveCount(0)
		await expect(page).toHaveURL(/sponsor_filters=/)
	})
})
