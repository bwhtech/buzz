// The dashboard's `__` fetches translations through useCall; islands read what the page already has.
export function translate(message: string, replace: any[] | Record<string, any> = []): string {
	const translated = window.translatedMessages?.[message] || message
	const values = replace as Record<string, unknown>
	return translated.replace(/{(\d+)}/g, (match, index) => String(values[index] ?? match))
}
