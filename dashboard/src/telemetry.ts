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

// Product analytics, apart from Pulse. The script is not bundled: it loads PostHog from its CDN.
export function loadPosthog(): void {
	if (!window.posthog_config) return
	const script = document.createElement("script")
	script.src = "/assets/buzz/js/lib/posthog.js"
	document.head.append(script)
}

// Frames that blocked the page for longer than an interaction may take (INP's "good"
// limit), to find what makes it feel slow. Sampled per page load and capped, so a busy
// session doesn't flood PostHog. Only code locations and the route pattern are sent.
const LONG_FRAME_MS = 200
const LONG_FRAME_SAMPLE_RATE = 0.1
const LONG_FRAME_LIMIT = 20

interface LongAnimationFrameScript {
	duration: number
	invokerType: string
	sourceURL: string
	sourceFunctionName: string
}

interface LongAnimationFrame extends PerformanceEntry {
	blockingDuration: number
	scripts: LongAnimationFrameScript[]
}

function scriptPath(url: string) {
	try {
		return new URL(url, location.origin).pathname
	} catch {
		return ""
	}
}

function longFrameProperties(frame: LongAnimationFrame, router: Router) {
	const script = frame.scripts.reduce<LongAnimationFrameScript | undefined>(
		(longest, current) => (!longest || current.duration > longest.duration ? current : longest),
		undefined,
	)
	return {
		duration: Math.round(frame.duration),
		blocking_duration: Math.round(frame.blockingDuration),
		route: routePattern(router.currentRoute.value),
		script_source: script ? scriptPath(script.sourceURL) : null,
		script_function: script?.sourceFunctionName || null,
		script_invoker_type: script?.invokerType || null,
	}
}

export function captureLongFrames(router: Router): void {
	if (!window.posthog_config || Math.random() >= LONG_FRAME_SAMPLE_RATE) return
	if (!PerformanceObserver.supportedEntryTypes?.includes("long-animation-frame")) return
	let captured = 0
	const observer = new PerformanceObserver((list) => {
		for (const frame of list.getEntries() as LongAnimationFrame[]) {
			if (frame.duration < LONG_FRAME_MS || captured >= LONG_FRAME_LIMIT) continue
			window.posthog?.capture("long_animation_frame", longFrameProperties(frame, router))
			captured += 1
		}
		if (captured >= LONG_FRAME_LIMIT) observer.disconnect()
	})
	observer.observe({ type: "long-animation-frame", buffered: true })
}
