interface Window {
	timezone?: {
		system?: string
		user?: string
	}
	site_name?: string
	google_place_search_enabled?: boolean
	google_maps_embed_api_key?: string | null
	zoom_available?: boolean
	playground?: {
		signup_url: string | null
		sandbox: string | null
		hours_left: number | null
	} | null
	personal_teams_enabled?: boolean
	posthog_config?: {
		api_key: string
		host: string
		sandbox: string | null
		persona: string | null
	} | null
	posthog?: { capture(event: string, properties?: Record<string, unknown>): void }
}

declare module "*.wav" {
	const value: string
	export default value
}

declare module "*.mp3" {
	const value: string
	export default value
}

declare module "*.svg" {
	const value: string
	export default value
}

// Virtual icon components from unplugin-icons (e.g. ~icons/lucide/check).
declare module "~icons/*" {
	import type { FunctionalComponent, SVGAttributes } from "vue"
	const component: FunctionalComponent<SVGAttributes>
	export default component
}
