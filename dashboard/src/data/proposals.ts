import type { ProposalListItem } from "@/types"
import { createResource } from "frappe-ui"

export const myProposals = createResource<ProposalListItem[]>({
	url: "buzz.api.proposals.get_my_proposals",
	cache: "My Proposals",
	auto: true,
})
