const DEFAULT_TARGET = "/b"

export function resolveLoginRedirect(redirectTo: unknown, origin: string): string {
	if (typeof redirectTo !== "string" || !redirectTo) return DEFAULT_TARGET
	try {
		const url = new URL(redirectTo, origin)
		if (url.origin !== origin) return DEFAULT_TARGET
		return url.pathname + url.search + url.hash
	} catch {
		return DEFAULT_TARGET
	}
}
