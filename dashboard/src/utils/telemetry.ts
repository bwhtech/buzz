import type { RouteLocationNormalized } from "vue-router"

export const DEFAULT_PULSE_CLIENT_URL =
	"https://pulse.m.frappe.cloud/assets/pulse/js/pulse_client.js"

export function trustedClientUrl(clientUrl: string | undefined, host: string | undefined): string {
	if (!clientUrl) return DEFAULT_PULSE_CLIENT_URL
	try {
		const target = new URL(clientUrl)
		if (target.protocol !== "https:") return DEFAULT_PULSE_CLIENT_URL
		const allowedOrigins = [new URL(DEFAULT_PULSE_CLIENT_URL).origin]
		if (host) allowedOrigins.push(new URL(host).origin)
		return allowedOrigins.includes(target.origin) ? clientUrl : DEFAULT_PULSE_CLIENT_URL
	} catch {
		return DEFAULT_PULSE_CLIENT_URL
	}
}

export function routePattern(route: Pick<RouteLocationNormalized, "matched" | "path">): string {
	return route.matched[route.matched.length - 1]?.path || route.path
}
