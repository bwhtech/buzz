import type { SetApprovalResult } from "@/types"
import type { BadgeTheme } from "@/utils/badgeTheme"

export type ApprovalState = "pending" | "declined" | "withdrawn" | "expired"

interface BookingStatus {
	status?: string | null
	requires_approval?: boolean | 0 | 1
}

/** Where a booking sits in the organizer's approval flow; null when approval is not involved. */
export function approvalState({ status, requires_approval }: BookingStatus): ApprovalState | null {
	if (status === "Withdrawn") return "withdrawn"
	if (status === "Expired") return "expired"
	if (!requires_approval) return null
	if (status === "Approval Pending") return "pending"
	return status === "Rejected" ? "declined" : null
}

const BADGES: Record<string, { label: string; theme: BadgeTheme }> = {
	"Approval Pending": { label: "Pending approval", theme: "amber" },
	Rejected: { label: "Declined", theme: "red" },
	Withdrawn: { label: "Withdrawn", theme: "gray" },
	Expired: { label: "Expired", theme: "gray" },
	Approved: { label: "Approved", theme: "green" },
	Confirmed: { label: "Confirmed", theme: "green" },
}

export function bookingStatusBadge(status: string): { label: string; theme: BadgeTheme } {
	return BADGES[status] ?? { label: status, theme: "red" }
}

/** A booking needs approval when the event asks for it on every ticket, or any chosen type does. */
export function needsApproval(
	eventRequiresApproval: boolean,
	chosenTicketTypes: string[],
	requiresApprovalByType: Record<string, boolean | undefined>,
): boolean {
	return eventRequiresApproval || chosenTicketTypes.some((name) => requiresApprovalByType[name])
}

export function approvalResultMessage(result: SetApprovalResult): string | null {
	const { approved, failed, declined } = result
	if (failed) return `${approved} approved, ${failed} couldn't fit — still pending`
	if (approved) return `${approved} approved`
	return declined ? `${declined} declined` : null
}
