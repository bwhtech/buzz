import {
	type APIRequestContext,
	type Page,
	request as playwrightRequest,
	expect,
	test,
} from "@playwright/test"

import { createUserWithRoles, saveLoginState } from "../helpers/auth"
import {
	callMethod,
	createDoc,
	deleteDoc,
	ensureEventHost,
	ensureTestTeam,
	getDoc,
	getList,
	updateDoc,
} from "../helpers/frappe"

interface NamedDoc {
	name: string
}

const enquiryCard = (page: Page, company: string) =>
	page.getByRole("button", { name: `Open ${company} enquiry` })

const drawer = (page: Page) => page.getByRole("dialog")

const PNG_FILE = {
	name: "e2e-logo.png",
	mimeType: "image/png",
	buffer: Buffer.from(
		"89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000000020001e221bc330000000049454e44ae426082",
		"hex",
	),
}

const PASSWORD = "Sponsor@123"
const OWNER = {
	email: "sponsorship-owner-e2e@buzz.test",
	statePath: "e2e/.auth/sponsorship-owner.json",
}

// Plain dashboard users: no team and no admin role, so only ownership grants access.
async function seedPlainUser(
	request: APIRequestContext,
	baseURL: string,
	user: { email: string; statePath: string },
) {
	await createUserWithRoles(request, {
		email: user.email,
		firstName: "Sponsor",
		password: PASSWORD,
		roles: ["Buzz User"],
	})
	await updateDoc(request, "User", user.email, { buzz_onboarding_status: "Completed" })
	await saveLoginState(baseURL, { ...user, password: PASSWORD })
}

// Files records as the plain user by API token; the empty session stops Administrator cookies outranking it.
async function apiContextWithKeys(request: APIRequestContext, baseURL: string, email: string) {
	const { api_secret } = await callMethod<{ api_secret: string }>(
		request,
		"frappe.core.doctype.user.user.generate_keys",
		{ user: email },
	)
	const { api_key } = await getDoc<{ api_key: string }>(request, "User", email)
	return playwrightRequest.newContext({
		baseURL,
		storageState: { cookies: [], origins: [] },
		extraHTTPHeaders: { Authorization: `token ${api_key}:${api_secret}` },
	})
}

// Runs under the shared Administrator state, who owns every enquiry it files here. Seeds its
// own event, and company names carry the run's timestamp, so no other spec's rows meet these.
test.describe("My sponsorships", () => {
	const run = Date.now()
	const approved = `Approved Co ${run}`
	const pending = `Pending Co ${run}`
	const paid = `Paid Co ${run}`
	const enquiries: Record<string, string> = {}
	let event: string

	const ownedCompany = `Owned Co ${run}`

	test.beforeAll(async ({ request, baseURL }) => {
		await seedPlainUser(request, baseURL!, OWNER)
		const team = await ensureTestTeam(request)
		event = (
			await createDoc<NamedDoc>(request, "Buzz Event", {
				team,
				title: `My Sponsorships ${run}`,
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
		const file = async (company_name: string, status: string, filer = request) => {
			const enquiry = await createDoc<NamedDoc>(filer, "Sponsorship Enquiry", {
				event,
				tier: tier.name,
				company_name,
				company_logo: "/assets/buzz/images/buzz-logo.png",
				status,
			})
			enquiries[company_name] = enquiry.name
		}
		await file(approved, "Payment Pending")
		await file(pending, "Approval Pending")
		await file(paid, "Paid")
		const ownerApi = await apiContextWithKeys(request, baseURL!, OWNER.email)
		await file(ownedCompany, "Approval Pending", ownerApi)
		await ownerApi.dispose()
	})

	test.afterAll(async ({ request }) => {
		for (const name of Object.values(enquiries)) {
			await deleteDoc(request, "Sponsorship Enquiry", name)
		}
		for (const tier of await getList<NamedDoc>(request, "Sponsorship Tier", {
			filters: { event },
		})) {
			await deleteDoc(request, "Sponsorship Tier", tier.name).catch(() => {})
		}
	})

	test("lists the enquiry and offers payment once it is approved", async ({ page }) => {
		await page.goto("/b/manage/sponsorship")

		await enquiryCard(page, approved).click()

		await expect(drawer(page).getByText("Payment Pending").first()).toBeVisible()
		await expect(drawer(page).getByText("₹50,000")).toBeVisible()
		await drawer(page).getByRole("button", { name: "Pay now" }).click()
		await expect(page.getByText("Select Sponsorship Tier")).toBeVisible()
	})

	test("opens the linked enquiry in its drawer", async ({ page }) => {
		await page.goto(`/b/manage/sponsorship?enquiry=${enquiries[pending]}`)

		await expect(drawer(page).getByRole("heading", { name: pending })).toBeVisible()
		await expect(page).toHaveURL(/\/b\/manage\/sponsorship$/)
	})

	test("withdraws an enquiry", async ({ page }) => {
		await page.goto(`/b/manage/sponsorship?enquiry=${enquiries[pending]}`)

		await drawer(page).getByRole("button", { name: "Withdraw" }).click()
		await page
			.getByRole("dialog", { name: "Withdraw this enquiry?" })
			.getByRole("button", { name: "Withdraw" })
			.click()

		await expect(page.getByText("Enquiry withdrawn")).toBeVisible()
		// The drawer stays open, so the refreshed row shows there; the card is behind its modal.
		await expect(drawer(page).getByText("Withdrawn").first()).toBeVisible()
	})

	test("celebrates a paid enquiry on the way back from the payment page", async ({ page }) => {
		await page.goto(`/b/manage/sponsorship?enquiry=${enquiries[paid]}&success=true`)

		await expect(drawer(page).getByText("Payment successful")).toBeVisible()
		await expect(drawer(page).getByRole("button", { name: "Pay now" })).toHaveCount(0)
		await expect(page).toHaveURL(/\/b\/manage\/sponsorship$/)
	})

	// Own contexts keep the Administrator session, which seeds and cleans up, out of these checks.
	test("a plain user opens their own enquiry and replaces its logo", async ({
		browser,
		request,
	}) => {
		const context = await browser.newContext({ storageState: OWNER.statePath })
		const page = await context.newPage()
		await page.goto("/b/manage/sponsorship")

		await enquiryCard(page, ownedCompany).click()

		await expect(drawer(page).getByRole("heading", { name: ownedCompany })).toBeVisible()
		await expect(enquiryCard(page, approved)).toHaveCount(0)

		await drawer(page).locator('input[type="file"]').setInputFiles(PNG_FILE)
		await page.getByRole("button", { name: "Save", exact: true }).click()
		await expect(page.getByText("Logo updated")).toBeVisible()
		const saved = await getDoc<{ company_logo: string }>(
			request,
			"Sponsorship Enquiry",
			enquiries[ownedCompany],
		)
		expect(saved.company_logo).not.toBe("/assets/buzz/images/buzz-logo.png")
		await context.close()
	})
})
