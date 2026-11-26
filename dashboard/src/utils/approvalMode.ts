export type ApprovalMode = "auto" | "manual" | "some"

interface TicketTypeFlags {
	name: string
	requires_approval: boolean
}

export const APPROVAL_MODES: {
	value: ApprovalMode
	title: string
	description: string
	icon: string
}[] = [
	{
		value: "auto",
		title: "Auto-confirm",
		description: "Everyone who registers gets in right away",
		icon: "lucide-zap",
	},
	{
		value: "manual",
		title: "Manual review",
		description: "You accept or decline every registration",
		icon: "lucide-shield-check",
	},
	{
		value: "some",
		title: "Review some tickets",
		description: "Pick which ticket types need your review",
		icon: "lucide-sliders-horizontal",
	},
]

/** Not stored: read off the event flag and the ticket type flags. */
export function approvalModeOf(
	eventRequiresApproval: boolean,
	ticketTypes: TicketTypeFlags[],
): ApprovalMode {
	if (eventRequiresApproval) return "manual"
	return ticketTypes.some((ticketType) => ticketType.requires_approval) ? "some" : "auto"
}

/** What picking a mode writes: the event flag, and the ticket types to clear. */
export function approvalModeWrites(mode: ApprovalMode, ticketTypes: TicketTypeFlags[]) {
	return {
		requires_approval: mode === "manual",
		clearTicketTypes:
			mode === "auto"
				? ticketTypes.filter((ticketType) => ticketType.requires_approval).map((row) => row.name)
				: [],
	}
}

/** What the event decides for every ticket type, which the ticket type drawer defers to. */
export interface TicketTypeAccess {
	mode: ApprovalMode
	eventWaitlist: boolean
}

type AccessValues = { requires_approval: boolean; enable_waitlist: boolean }

/** The ticket type's switches show what applies to it, the event's flags included. */
export function withEventAccess<T extends AccessValues>(values: T, access: TicketTypeAccess): T {
	return {
		...values,
		requires_approval: values.requires_approval || access.mode === "manual",
		enable_waitlist: values.enable_waitlist || access.eventWaitlist,
	}
}

export function accessChanged(before: AccessValues, after: AccessValues): boolean {
	return (
		before.requires_approval !== after.requires_approval ||
		before.enable_waitlist !== after.enable_waitlist
	)
}
