// frappe-ui ships `frappe-ui/vite` as plain JavaScript with no declarations. The
// options below are the ones its plugins actually read, so a key it silently
// ignores becomes a type error rather than dead config.
declare module "frappe-ui/vite" {
	import type { Plugin } from "vite"

	interface FrappeProxyOptions {
		port?: number
		source?: string
	}

	interface BuildConfigOptions {
		outDir?: string
		indexHtmlPath?: string
		baseUrl?: string
		emptyOutDir?: boolean
		sourcemap?: boolean
	}

	interface LucideIconOptions {
		componentGlobs?: string[]
	}

	interface FrappeUIOptions {
		frontendRoute?: string
		lucideIcons?: boolean | LucideIconOptions
		frappeProxy?: boolean | FrappeProxyOptions
		jinjaBootData?: boolean
		buildConfig?: boolean | BuildConfigOptions
		frappeTypes?: Record<string, unknown>
	}

	export default function frappeui(options?: FrappeUIOptions): Plugin[]
}
