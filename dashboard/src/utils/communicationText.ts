// Editor HTML with the tags stripped: for the history row's excerpt and the "is there
// anything to send" test, where an empty paragraph must count as nothing.
export function plainText(html: string): string {
	return html
		.replace(/<[^>]+>/g, " ")
		.replace(/&nbsp;/g, " ")
		.replace(/\s+/g, " ")
		.trim()
}

export const hasText = (html: string) => plainText(html).length > 0

export function excerpt(html: string, length = 90): string {
	const text = plainText(html)
	return text.length > length ? `${text.slice(0, length).trimEnd()}…` : text
}

// One list for the composer and the drawer, so the two selects always agree.
export const audienceOptions = [
	{ value: "Guests", label: "Guests", icon: "lucide-users-round" },
	{ value: "Speakers", label: "Speakers", icon: "lucide-megaphone" },
]
