import { useCall, useDoc } from "frappe-ui"

import type { AcceptedProposal, ProposalListItem, ProposalTrend, TalkProposal } from "@/types"

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
// Uncached: cacheKey would persist this user's proposals to IndexedDB past a logout.
export function useMyProposals() {
	return useCall<ProposalListItem[]>({
		url: "/api/v2/method/buzz.api.proposals.get_my_proposals",
	})
}

/**
 * The full document behind one proposal card: its description, speakers and the answers
 * to the event's own form questions, none of which the list call carries.
 *
 * A listed speaker holds write on their own proposal, so the same document is what the
 * drawer withdraws through and appends speakers to.
 */
export function useProposal(name: () => string | undefined) {
	// useDoc holds its initial fetch until the name resolves, so the empty string is
	// only ever the drawer before a card has been picked.
	return useDoc<TalkProposal>({ doctype: "Talk Proposal", name: () => name() || "" })
}

// The card above an event's proposal list: how many have come in, and their split.
export function useProposalTrend(event: string) {
	return useCall<ProposalTrend, { event: string }>({
		url: "/api/v2/method/buzz.api.proposals.get_event_proposal_trend",
		params: { event },
	})
}

/**
 * Accepting is not a status write.
 *
 * `create_talk` behind this endpoint builds the Event Talk the programme is made of, and
 * an account for any speaker who has none. Setting the status alone would leave the
 * proposal accepted with nothing on the programme, and no way back to make one.
 */
export function useAcceptProposal() {
	return useCall<AcceptedProposal, { proposal: string }>({
		url: "/api/v2/method/buzz.api.proposals.accept_proposal",
		method: "POST",
		immediate: false,
	})
}
