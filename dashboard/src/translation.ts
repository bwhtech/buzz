import { createResource } from "frappe-ui"
import type { App } from "vue"

// replace accepts positional values ({0}, {1}, ...) or a keyed map; values may
// be numbers, so keep it loose to match the many mixed-arg call sites.
type TranslateFn = (
	message: string,
	replace?: any[] | Record<string, any>,
	context?: string | null,
) => string

declare global {
	interface Window {
		__: TranslateFn
		translatedMessages?: Record<string, string>
	}

	// Bare `__(...)` calls in scripts resolve to this global; keep it aligned
	// with TranslateFn so script and template call sites share one signature.
	const __: TranslateFn
}

// `__` is registered on globalProperties so templates can call it directly.
declare module "vue" {
	interface ComponentCustomProperties {
		__: TranslateFn
	}
}

export default function translationPlugin(app: App) {
	app.config.globalProperties.__ = translate
	window.__ = translate
	if (!window.translatedMessages) fetchTranslations()
}

function format(message: string, replace: any[] | Record<string, any>): string {
	const values = replace as Record<string, any>
	return message.replace(/{(\d+)}/g, (match, number) =>
		typeof values[number] != "undefined" ? values[number] : match,
	)
}

const translate: TranslateFn = (message, replace, context = null) => {
	const translatedMessages = window.translatedMessages || {}
	let translatedMessage = ""

	if (context) {
		const key = `${message}:${context}`
		if (translatedMessages[key]) {
			translatedMessage = translatedMessages[key]
		}
	}

	if (!translatedMessage) {
		translatedMessage = translatedMessages[message] || message
	}

	const hasPlaceholders = /{\d+}/.test(message)
	if (!hasPlaceholders) {
		return translatedMessage
	}

	return format(translatedMessage, replace ?? [])
}

function fetchTranslations(_lang?: string) {
	createResource({
		url: "buzz.api.get_translations",
		auto: true,
		transform: (data: Record<string, string>) => {
			window.translatedMessages = data
		},
	})
}
