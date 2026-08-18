import type { ProposalListItem } from "@/types"
import { useCall } from "frappe-ui"

// v2 path: useCall reads the payload from `data`, which /api/method names `message`.
// Uncached: cacheKey would persist this user's proposals to IndexedDB past a logout.
export function useMyProposals() {
	return useCall<ProposalListItem[]>({
		url: "/api/v2/method/buzz.api.proposals.get_my_proposals",
	})
}
