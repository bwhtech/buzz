import type { Router } from "vue-router"

import { routePattern } from "@/utils/telemetry"

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
