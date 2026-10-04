<script setup lang="ts">
import { call, toast } from "frappe-ui"
import { computed, ref } from "vue"

import QuickActionsRail, {
	type QuickAction,
} from "@/components/dashboard/events/QuickActionsRail.vue"
import ProposalsDialog from "@/components/dashboard/proposals/ProposalsDialog.vue"
import type { EventProposals, ProposalListItem } from "@/types"
import { downloadCsv } from "@/utils/csv"

const props = defineProps<{
	event: string
	closed: boolean
	canWrite: boolean
	title?: string | null
	proposalLink?: string | null
	// What the list is currently showing, so the export is the same list.
	query: { search: string; statuses: string; order: string }
}>()
const emit = defineEmits<{ changed: [] }>()

const dialogOpen = ref(false)
const exporting = ref(false)

// The list is paged, so the export walks it: a hundred at a time until the server says
// there is no next page.
async function fetchAll(): Promise<ProposalListItem[]> {
	const all: ProposalListItem[] = []
	for (let start = 0; ; start += 100) {
		const page: EventProposals = await call("buzz.api.proposals.get_event_proposals", {
			event: props.event,
			...props.query,
			start,
			limit: 100,
		})
		all.push(...page.proposals)
		if (!page.has_next_page) return all
	}
}

const speakerNames = (proposal: ProposalListItem) =>
	proposal.speakers.map((speaker) => [speaker.first_name, speaker.last_name].join(" ").trim())

async function exportProposals() {
	exporting.value = true
	try {
		const proposals = await fetchAll()
		downloadCsv(`${props.title || "proposals"} - talks.csv`, [
			["Title", "Speakers", "Emails", "Status", "Submitted at"],
			...proposals.map((proposal) => [
				proposal.title,
				speakerNames(proposal).join(", "),
				proposal.speakers.map((speaker) => speaker.email).join(", "),
				proposal.status,
				proposal.creation,
			]),
		])
	} catch {
		toast.error("Could not export the proposals. Try again.")
	} finally {
		exporting.value = false
	}
}

const actions = computed<QuickAction[]>(() =>
	[
		props.proposalLink
			? { icon: "lucide-arrow-up-right", label: "Proposal page", link: props.proposalLink }
			: null,
		{
			icon: "lucide-download",
			label: "Download CSV",
			loading: exporting.value,
			onClick: exportProposals,
		},
	].filter((action) => action !== null),
)
</script>

<template>
	<QuickActionsRail
		subject="Proposals"
		open-icon="lucide-mic"
		closed-icon="lucide-mic-off"
		:closed="closed"
		:can-write="canWrite"
		:actions="actions"
		@toggle="dialogOpen = true"
	/>

	<ProposalsDialog
		v-model="dialogOpen"
		:event="event"
		:closed="closed"
		@changed="emit('changed')"
	/>
</template>
