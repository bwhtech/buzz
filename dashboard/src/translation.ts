import { createResource } from "frappe-ui"
import type { App } from "vue"

type TranslateFn = (
	message: string,
	replace?: Record<string, string> | string[],
	context?: string | null,
) => string

declare global {
	interface Window {
		__: TranslateFn
		translatedMessages?: Record<string, string>
	}
}

export default function translationPlugin(app: App) {
	app.config.globalProperties.__ = translate
	window.__ = translate
	if (!window.translatedMessages) fetchTranslations()
}

function format(
	message: string,
	replace: Record<string, string> | string[],
): string {
	return message.replace(/{(\d+)}/g, (match, number) =>
		typeof replace[number] != "undefined" ? replace[number] : match,
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
