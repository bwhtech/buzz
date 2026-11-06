import type { RouteLocationNormalized } from "vue-router"

export function routePattern(route: Pick<RouteLocationNormalized, "matched" | "path">): string {
	return route.matched[route.matched.length - 1]?.path || route.path
}
