import { call } from "frappe-ui"
import type { RouteLocationNormalized, Router } from "vue-router"

import { session } from "@/data/session"
import { routePattern, trustedClientUrl } from "@/utils/telemetry"

const APP_NAME = "buzz"
const BOOT_CONFIG_METHOD = "frappe.utils.telemetry.pulse.client.boot_config"
const PAGEVIEW_MAX_SITE_AGE = 15

interface BootConfig {
	enabled?: boolean
	host?: string
	key?: string
	site?: string
	user?: string
	team?: string
	client_url?: string
	site_age?: number
}

interface PulseClient {
	init(): Promise<boolean>
	capture(eventName: string, app: string, properties?: Record<string, unknown>): void
}

async function fetchBootConfig(): Promise<BootConfig> {
	try {
		return ((await call(BOOT_CONFIG_METHOD)) as BootConfig) || {}
	} catch {
		return {}
	}
}

async function loadPulseClient(config: BootConfig): Promise<PulseClient | null> {
	try {
		const module = await import(/* @vite-ignore */ trustedClientUrl(config.client_url, config.host))
		return new module.PulseClient({
			host: config.host,
			apiKey: config.key,
			site: config.site,
			enabled: true,
			getContext: () => ({ user: config.user, team: config.team }),
		}) as PulseClient
	} catch {
		return null
	}
}

function trackPageviews(client: PulseClient, router: Router): void {
	let lastFullPath = ""
	const capturePageview = (route: RouteLocationNormalized) => {
		if (route.fullPath === lastFullPath) return
		lastFullPath = route.fullPath
		try {
			client.capture("pageview", APP_NAME, { route: routePattern(route) })
		} catch {
			// The client is remote code; a throw here would reject the navigation.
		}
	}

	router.isReady().then(() => capturePageview(router.currentRoute.value))
	router.afterEach((route) => capturePageview(route))
}

export async function installTelemetry(router: Router): Promise<void> {
	if (!session.isLoggedIn) return

	const config = await fetchBootConfig()
	if (!config.enabled) return
	if (config.site_age && config.site_age > PAGEVIEW_MAX_SITE_AGE) return

	const client = await loadPulseClient(config)
	if (!client || !(await client.init())) return

	trackPageviews(client, router)
}
