import type { BadgeTheme } from "@/utils/badgeTheme"

export type RegistrationRequestStatus = "Requested" | "Waitlisted" | "Payment Pending" | "Rejected"

export interface RequestNotice {
	title: string
	message: string
	theme: BadgeTheme
	canPay: boolean
}

interface RequestFlags {
	needs_approval?: boolean
	waitlisted?: boolean
}

const NOTICES: Record<RegistrationRequestStatus, RequestNotice> = {
	Requested: {
		title: "Request received",
		message: "The organizer will review it. We'll email you once they decide.",
		theme: "amber",
		canPay: false,
	},
	Waitlisted: {
		title: "You're on the waitlist",
		message: "We'll email you if a spot opens.",
		theme: "gray",
		canPay: false,
	},
	"Payment Pending": {
		title: "You're approved",
		message: "Pay to confirm your spot.",
		theme: "amber",
		canPay: true,
	},
	Rejected: {
		title: "Your request wasn't approved",
		message: "The organizer couldn't confirm your spot this time.",
		theme: "red",
		canPay: false,
	},
}

export function requestNotice(status?: string | null): RequestNotice | null {
	return NOTICES[status as RegistrationRequestStatus] ?? null
}

/** Requests are free until approved, so the guest picks no payment method. */
export function isRegistrationRequest(pickedTicketTypes: RequestFlags[]): boolean {
	return pickedTicketTypes.some((ticketType) => ticketType.waitlisted || ticketType.needs_approval)
}

export function requestSubmitLabel(pickedTicketTypes: RequestFlags[]): string | null {
	if (pickedTicketTypes.some((ticketType) => ticketType.waitlisted)) return "Join waitlist"
	return isRegistrationRequest(pickedTicketTypes) ? "Request to join" : null
}
