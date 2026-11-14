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

export type TransactionStatus = { label: string; theme: BadgeTheme }

/** One status for the money: a refund outranks the payment it undoes. */
export function transactionStatus(row: {
	payment_status: string | null
	refund_status: string | null
}): TransactionStatus {
	const { payment_status, refund_status } = row
	if (refund_status) return { label: refund_status, theme: refundStatusTheme(refund_status) }
	if (payment_status === "Verification Pending")
		return { label: "Pending verification", theme: "amber" }
	return { label: payment_status || "Unpaid", theme: paymentStatusTheme(payment_status) }
}

const BOOKING_STATUS_THEMES: Record<string, BadgeTheme> = {
	Confirmed: "green",
	Approved: "green",
	"Payment Pending": "amber",
	"Approval Pending": "amber",
	Requested: "blue",
	Invited: "blue",
	Rejected: "red",
}

/** A booking status change in the activity feed, coloured like its meaning. */
export const bookingStatusTheme = (status: string): BadgeTheme =>
	BOOKING_STATUS_THEMES[status] ?? "gray"
