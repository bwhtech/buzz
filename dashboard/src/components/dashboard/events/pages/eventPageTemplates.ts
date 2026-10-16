export type EventPageTemplate = {
	title: string
	icon: string
	description: string
	content: string
}

export const blankPageIcon = "lucide-file-text"

// Starter copy only: every line is meant to be rewritten for the event.
export const eventPageTemplates: EventPageTemplate[] = [
	{
		title: __("Code of conduct"),
		icon: "lucide-shield-check",
		description: __("Set expectations for how guests treat each other"),
		content: `<p>${__("We want this event to feel welcoming for everyone. By attending, you agree to:")}</p><ul><li><p>${__("Be kind and respectful to other guests, speakers and staff")}</p></li><li><p>${__("Ask before taking photos of people")}</p></li><li><p>${__("Report anything that feels off to the organisers")}</p></li></ul><h3>${__("Reporting")}</h3><p>${__("Talk to any organiser at the venue. Reports stay confidential.")}</p>`,
	},
	{
		title: __("FAQ"),
		icon: "lucide-circle-help",
		description: __("Answer common questions before they get asked"),
		content: `<h3>${__("Can I bring a friend?")}</h3><p>${__("Each guest needs their own registration.")}</p><h3>${__("Is there parking?")}</h3><p>${__("Add parking details here.")}</p>`,
	},
	{
		title: __("Refund policy"),
		icon: "lucide-receipt",
		description: __("Explain cancellations and refunds"),
		content: `<p>${__("Cancel up to 48 hours before the event for a full refund. After that, you can transfer your ticket to someone else.")}</p>`,
	},
	{
		title: __("Venue & travel"),
		icon: "lucide-map-pin",
		description: __("Share directions, parking and nearby stays"),
		content: `<p>${__("Add directions to the venue, the nearest transit stop and where to park.")}</p>`,
	},
]

export function eventPageIcon(title: string) {
	return eventPageTemplates.find((template) => template.title === title)?.icon ?? blankPageIcon
}
