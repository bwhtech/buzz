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

interface AccessSwitch {
	disabled: boolean
	// Shown instead of the stored value while the event decides it.
	forced?: boolean
	description: string
}

/** The ticket type's own approval switch: only free to change under "Review some tickets". */
export function approvalSwitch(mode: ApprovalMode): AccessSwitch {
	if (mode === "manual")
		return {
			disabled: true,
			forced: true,
			description: "On for all tickets — change in Registration approval",
		}
	if (mode === "auto")
		return {
			disabled: true,
			forced: false,
			description: "Off for all tickets — change in Registration approval",
		}
	return { disabled: false, description: "Registrations wait in Approvals until you accept them" }
}

/** The event waitlist covers every ticket type with a seat limit; a ticket type can add its own. */
export function waitlistSwitch(eventWaitlist: boolean, hasSeatLimit: boolean): AccessSwitch {
	if (!hasSeatLimit)
		return { disabled: true, forced: false, description: "Set a seat limit to enable a waitlist" }
	if (eventWaitlist)
		return {
			disabled: true,
			forced: true,
			description: "On for all sold-out tickets — change in Registration",
		}
	return { disabled: false, description: "People can join a waitlist once every seat is taken" }
}
