import { type Page, expect, test } from "@playwright/test"

const PULSE_HOST = "https://pulse.test"
const PULSE_CLIENT_URL = "https://pulse.m.frappe.cloud/assets/pulse/js/pulse_client.js"

const STUB_CLIENT = `
export class PulseClient {
	constructor(options) { this.options = options }
	async init() { return this.options.enabled }
	setEnabled() {}
	capture(event, app, properties) {
		window.__pulseCaptures = window.__pulseCaptures || []
		window.__pulseCaptures.push({ event, app, properties })
	}
	getDistinctId() { return "stub" }
	flush() {}
	stop() {}
}
`

interface Capture {
	event: string
	app: string
	properties: Record<string, unknown>
}

async function stubPulse(page: Page, enabled: boolean): Promise<string[]> {
	const pulseRequests: string[] = []

	await page.route("**/api/method/frappe.utils.telemetry.pulse.client.boot_config", (route) =>
		route.fulfill({
			json: {
				message: enabled
					? {
							enabled: true,
							host: PULSE_HOST,
							client_url: PULSE_CLIENT_URL,
							key: "test-key",
							site: "buzz.test",
							user: "anon-user",
							site_age: 1,
						}
					: { enabled: false },
			},
		}),
	)
	await page.route(PULSE_CLIENT_URL, (route) =>
		route.fulfill({
			body: STUB_CLIENT,
			contentType: "application/javascript",
			headers: { "access-control-allow-origin": "*" },
		}),
	)
	await page.route(`${PULSE_HOST}/**`, (route) => {
		pulseRequests.push(route.request().url())
		return route.abort()
	})

	return pulseRequests
}

async function captures(page: Page): Promise<Capture[]> {
	return page.evaluate(
		() => (window as unknown as { __pulseCaptures?: Capture[] }).__pulseCaptures ?? [],
	)
}

test.describe("Telemetry", () => {
	test("sends a pageview with the route pattern, never the real url", async ({ page }) => {
		const pulseRequests = await stubPulse(page, true)

		await page.goto("/b/account/tickets/TICKET-SECRET-123")
		await expect.poll(async () => (await captures(page)).length).toBeGreaterThan(0)

		const [pageview] = await captures(page)
		expect(pageview).toEqual({
			event: "pageview",
			app: "buzz",
			properties: { route: "/account/tickets/:ticketId" },
		})
		expect(JSON.stringify(await captures(page))).not.toContain("TICKET-SECRET-123")
		expect(pulseRequests).toEqual([])
	})

	test("sends nothing when telemetry is off", async ({ page }) => {
		await stubPulse(page, false)

		await page.goto("/b/account/bookings")
		await page.waitForLoadState("networkidle")

		expect(await captures(page)).toEqual([])
	})

	test.describe("as a guest", () => {
		test.use({ storageState: { cookies: [], origins: [] } })

		test("does not load telemetry at all", async ({ page }) => {
			const bootConfigCalls: string[] = []
			page.on("request", (request) => {
				if (request.url().includes("boot_config")) bootConfigCalls.push(request.url())
			})
			await stubPulse(page, true)

			await page.goto("/b/event-proposal")
			await page.waitForLoadState("networkidle")

			expect(bootConfigCalls).toEqual([])
			expect(await captures(page)).toEqual([])
		})
	})
})
