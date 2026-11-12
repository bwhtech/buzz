import type { BadgeTheme } from "./badgeTheme.ts"

const PAYMENT_THEMES: Record<string, BadgeTheme> = {
	Paid: "green",
	"Verification Pending": "amber",
	Unpaid: "gray",
}

const REFUND_THEMES: Record<string, BadgeTheme> = {
	Refunded: "red",
	"Partially Refunded": "amber",
	"Refund Initiated": "blue",
}

export const paymentStatusTheme = (status: string | null): BadgeTheme =>
	PAYMENT_THEMES[status ?? ""] ?? "gray"

export const refundStatusTheme = (status: string | null): BadgeTheme =>
	REFUND_THEMES[status ?? ""] ?? "gray"

/** A gateway reference is long and opaque; its ends are what people match by eye. */
export function truncateMiddle(text: string, keep = 6): string {
	return text.length <= keep * 2 + 1 ? text : `${text.slice(0, keep)}…${text.slice(-keep)}`
}
