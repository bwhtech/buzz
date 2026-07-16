export {}

declare global {
	interface Window {
		timezone?: {
			system?: string
			user?: string
		}
		site_name?: string
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
}
