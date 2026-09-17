import { dayjsLocal } from "frappe-ui"
import { type Ref, ref, watch } from "vue"

export type BadgeTheme = "green" | "amber" | "blue" | "red" | "gray"

const ENQUIRY_STATUS_THEMES: Record<string, BadgeTheme> = {
	Paid: "green",
	"Payment Pending": "amber",
	"Approval Pending": "blue",
	Cancelled: "gray",
	Withdrawn: "red",
}

export const ENQUIRY_STATUSES = Object.keys(ENQUIRY_STATUS_THEMES)

const THEME_DOTS: Record<BadgeTheme, string> = {
	blue: "bg-[--ink-blue-5]",
	red: "bg-[--ink-red-5]",
	green: "bg-[--ink-green-5]",
	amber: "bg-[--ink-amber-5]",
	gray: "bg-[--ink-gray-5]",
}

export const enquiryStatusDot = (status: string) => THEME_DOTS[enquiryStatusTheme(status)]

export const enquiryStatusTheme = (status: string): BadgeTheme =>
	ENQUIRY_STATUS_THEMES[status] || "gray"

// Websites are typed freely, so a bare domain still needs a scheme to be a link.
export const websiteUrl = (website: string | null) =>
	website && (/^https?:\/\//i.test(website) ? website : `https://${website}`)

export const stripUrlScheme = (website: string) => website.replace(/^\s*https?:\/\//i, "")

// "2h ago" today, "Yesterday", then a short date — how a pipeline row reads at a glance.
export function shortSubmittedAt(creation: string) {
	const submitted = dayjsLocal(creation)
	const now = dayjsLocal()
	if (submitted.isSame(now, "day")) return submitted.fromNow()
	if (submitted.isSame(now.subtract(1, "day"), "day")) return "Yesterday"
	return submitted.format(submitted.isSame(now, "year") ? "D MMM" : "D MMM YYYY")
}

export const websiteLabel = (website: string | null) =>
	website
		?.replace(/^https?:\/\//i, "")
		.replace(/^www\./i, "")
		.replace(/\/$/, "") ?? ""

/**
 * Holds on to the last non-null value. A drawer keyed straight off the selection unmounts
 * the moment it clears, which skips its exit animation; this keeps the content in place
 * while the drawer slides out.
 */
export function keepLastValue<T>(current: () => T | null | undefined) {
	const last = ref<T | null>(null)
	watch(current, (value) => value && (last.value = value), { immediate: true })
	return last as Ref<T | null>
}
