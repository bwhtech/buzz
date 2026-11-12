// Mirrors INVITE_LIMIT in buzz/api/booking/invites.py.
export const INVITE_LIMIT = 100
export const MESSAGE_LIMIT = 300
export const TEMPLATE_COLUMNS = ["First Name", "Last Name", "Email", "Tier"]

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export type TierOption = { value: string; label: string }

export type Invitee = {
	id: number
	first_name: string
	last_name: string
	email: string
	// A ticket type name, or the sheet's own text until the organizer maps it.
	ticket_type: string
}

let lastId = 0

export function newInvitee(fields: Partial<Invitee> & { ticket_type: string }): Invitee {
	lastId += 1
	return { id: lastId, first_name: "", last_name: "", email: "", ...fields }
}

export const isValidEmail = (email: string) => EMAIL_PATTERN.test(email.trim())

export const emailKey = (email: string) => email.trim().toLowerCase()

export const guestCount = (count: number) => `${count} ${count === 1 ? "guest" : "guests"}`

export const needsName = (invitee: Pick<Invitee, "first_name">) => !invitee.first_name.trim()

export const displayName = (invitee: Pick<Invitee, "first_name" | "last_name" | "email">) =>
	[invitee.first_name, invitee.last_name].filter(Boolean).join(" ") || invitee.email

/** Splits pasted or typed text on commas, semicolons, spaces and newlines. */
export const splitEmails = (text: string) => text.split(/[\s,;]+/).filter(Boolean)

/** Sheet tiers are titles; a known title becomes its ticket type, a blank one the default. */
export function tierFromSheet(tier: string, tiers: TierOption[], fallback: string): string {
	if (!tier) return fallback
	const match = tiers.find((option) => option.label.toLowerCase() === tier.toLowerCase())
	return match?.value ?? tier
}

/** Rows repeating an earlier row's email; the first one stays. */
export function duplicateIds(invitees: Invitee[]): Set<number> {
	const seen = new Set<string>()
	const duplicates = new Set<number>()
	for (const row of invitees) {
		if (seen.has(emailKey(row.email))) duplicates.add(row.id)
		seen.add(emailKey(row.email))
	}
	return duplicates
}

export function rowProblem(
	invitee: Invitee,
	duplicates: Set<number>,
	tiers: TierOption[],
): string | null {
	if (!isValidEmail(invitee.email)) return "Invalid email"
	if (duplicates.has(invitee.id)) return "Already on the list"
	if (!tiers.some((tier) => tier.value === invitee.ticket_type)) return "Unknown tier"
	return null
}

export function readyInvitees(invitees: Invitee[], tiers: TierOption[]): Invitee[] {
	const duplicates = duplicateIds(invitees)
	return invitees.filter((row) => !rowProblem(row, duplicates, tiers))
}

export type Contact = Pick<Invitee, "first_name" | "last_name" | "email"> & { note: string }
