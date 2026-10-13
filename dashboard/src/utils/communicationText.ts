import type { Condition, FilterField } from "@/components/common/filters"

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
	{ value: "Sponsors", label: "Sponsors", icon: "lucide-handshake" },
]

// "Ticket type is VIP", the way the chip reads, for a message that was already sent.
export function describeCondition([key, operator, value]: Condition, fields: FilterField[]) {
	const field = fields.find((candidate) => candidate.key === key)
	if (!field) return null
	const choice = field.operators.find((option) => option.operator === operator)
	if (choice?.value) return `${field.label} ${choice.label}`
	const labels = new Map(field.options.map((option) => [option.value, option.label]))
	const values = (Array.isArray(value) ? value : [value]).map((item) => labels.get(item) || item)
	return `${field.label} ${choice?.label ?? operator} ${values.join(" or ")}`
}
