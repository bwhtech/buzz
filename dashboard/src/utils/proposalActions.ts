import type { ProposalListItem } from "@/types"

export interface ProposalActions {
	canEdit: boolean
	canWithdraw: boolean
	canManageSpeakers: boolean
}

const PENDING = "Review Pending"

/** A run that ends today is not over yet, so end_date decides — as the timeline does. */
function isOver(proposal: ProposalListItem, today: string): boolean {
	const last = proposal.end_date || proposal.start_date
	return Boolean(last) && (last as string) < today
}

/**
 * What the submitter may still do to their proposal.
 *
 * Nothing survives the event: once it is over the proposal is a record, not a draft.
 * Before then only a pending proposal is open.
 */
export function proposalActions(proposal: ProposalListItem, today: string): ProposalActions {
	if (isOver(proposal, today)) {
		return { canEdit: false, canWithdraw: false, canManageSpeakers: false }
	}

	// An accepted talk is edited through its Event Talk, not the proposal, so the drawer
	// leaves it alone even where allow_editing_talks_after_acceptance is on.
	const pending = proposal.status === PENDING

	return { canEdit: pending, canWithdraw: pending, canManageSpeakers: pending }
}
