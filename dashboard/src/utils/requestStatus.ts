import type { RegistrationRequest, RequestType } from "@/types"
import type { BadgeTheme } from "@/utils/badgeTheme"

export type RequestView =
	| "pending"
	| "awaiting"
	| "approved"
	| "declined"
	| "waiting"
	| "invited"
	| "registered"
	| "expired"
	| "removed"

export type RequestAction =
	| "approve"
	| "approve_anyway"
	| "decline"
	| "reopen"
	| "revoke"
	| "resend"

export interface RequestButton {
	action: RequestAction
	label: string
}

export const REQUEST_VIEWS: Record<RequestView, { label: string; theme: BadgeTheme }> = {
	pending: { label: "Pending", theme: "amber" },
	awaiting: { label: "Awaiting payment", theme: "blue" },
	approved: { label: "Approved", theme: "green" },
	declined: { label: "Declined", theme: "red" },
	waiting: { label: "Waiting", theme: "gray" },
	invited: { label: "Invited", theme: "blue" },
	registered: { label: "Registered", theme: "green" },
	expired: { label: "Expired", theme: "red" },
	removed: { label: "Removed", theme: "gray" },
}

/** The stat cards of each page, in order; each one is also a view of the list. */
export const STAT_VIEWS: Record<RequestType, { view: RequestView; label: string }[]> = {
	Approval: [
		{ view: "pending", label: "Pending review" },
		{ view: "awaiting", label: "Awaiting payment" },
		{ view: "approved", label: "Approved" },
		{ view: "declined", label: "Declined" },
	],
	Waitlist: [
		{ view: "waiting", label: "On waitlist" },
		{ view: "invited", label: "Invited" },
		{ view: "registered", label: "Registered" },
		{ view: "expired", label: "Expired" },
	],
}

export const OPEN_VIEW: Record<RequestType, RequestView> = {
	Approval: "pending",
	Waitlist: "waiting",
}

export function requestViewOf(row: RegistrationRequest): RequestView {
	const approval = row.request_type === "Approval"
	if (row.docstatus === 1) return approval ? "approved" : "registered"
	if (row.status === "Rejected") return approval ? "declined" : "removed"
	if (row.status === "Payment Pending") {
		if (approval) return "awaiting"
		return row.offer_expires_at ? "invited" : "expired"
	}
	return OPEN_VIEW[row.request_type]
}

/** Where a row lands once an action goes through, so it can move before the write does. */
export function viewAfter(action: RequestAction, type: RequestType, paid: boolean): RequestView {
	const approval = type === "Approval"
	if (action === "decline") return approval ? "declined" : "removed"
	if (action === "reopen" || action === "revoke") return OPEN_VIEW[type]
	if (action === "resend") return approval ? "awaiting" : "invited"
	if (approval) return paid ? "awaiting" : "approved"
	return paid ? "invited" : "registered"
}

const BUTTONS: Record<RequestView, (paid: boolean) => RequestButton[]> = {
	pending: (paid) => [
		{ action: "approve", label: paid ? "Approve & send link" : "Approve" },
		{ action: "decline", label: "Decline" },
	],
	awaiting: () => [
		{ action: "resend", label: "Resend payment link" },
		{ action: "revoke", label: "Revoke approval" },
	],
	approved: () => [],
	declined: () => [
		{ action: "approve_anyway", label: "Approve anyway" },
		{ action: "reopen", label: "Move to pending" },
	],
	waiting: (paid) => [
		{ action: "approve", label: paid ? "Let in & send link" : "Let in" },
		{ action: "decline", label: "Remove" },
	],
	invited: () => [
		{ action: "resend", label: "Resend link" },
		{ action: "revoke", label: "Revoke invite" },
	],
	expired: () => [
		{ action: "resend", label: "Invite again" },
		{ action: "revoke", label: "Back to waitlist" },
	],
	removed: () => [{ action: "reopen", label: "Back to waitlist" }],
	registered: () => [],
}

/** The drawer's buttons for a row, primary first. */
export function requestButtons(view: RequestView, paid: boolean): RequestButton[] {
	return BUTTONS[view](paid)
}

interface MessageSubject {
	type: RequestType
	// First names of everyone the action touched.
	names: string[]
	// The price of the one request, "" when free.
	price: string
}

/** The toast an action shows, as the design words it. */
export function actionMessage(action: RequestAction, subject: MessageSubject): string {
	const { type, names, price } = subject
	const count = names.length
	const first = names[0]
	const waitlist = type === "Waitlist"
	switch (action) {
		case "approve":
		case "approve_anyway":
			if (waitlist) {
				if (count > 1) return `Let in ${count} people from the waitlist`
				return price ? `Invited ${first} · payment link sent` : `Let in ${first} · ticket emailed`
			}
			if (count > 1) return `Approved ${count} requests`
			return price
				? `Approved ${first} · ${price} payment link sent`
				: `Approved ${first} · ticket emailed`
		case "decline":
			if (waitlist) return `Removed ${count > 1 ? count : first} from the waitlist`
			return count > 1 ? `Declined ${count} requests` : `Declined ${first}`
		case "resend":
			return count > 1
				? `Payment links resent to ${count} people`
				: `Payment link resent to ${first}`
		default:
			return `Moved ${first} back to ${waitlist ? "the waitlist" : "pending"}`
	}
}
