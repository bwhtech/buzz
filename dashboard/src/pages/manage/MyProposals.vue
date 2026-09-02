<script setup lang="ts">
import { Icon, dayjs } from "frappe-ui"
import { computed } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import CreateEventHeader from "@/components/dashboard/CreateEventHeader.vue"
import ProposalCard from "@/components/dashboard/proposals/ProposalCard.vue"
import ProposalDrawer from "@/components/dashboard/proposals/ProposalDrawer.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useDrawerSelection } from "@/composables/useDrawerSelection"
import { useMyProposals } from "@/data/proposals"
import type { ProposalWithEvent } from "@/types"
import { groupEventsByMonth } from "@/utils/eventGroups"
import { inTab, useTimelineTabQuery } from "@/utils/timelineTabs"

// In the URL, so one link carries the whole view.
const tab = useTimelineTabQuery()

const myProposals = useMyProposals()

const drawer = useDrawerSelection<ProposalWithEvent>()

// The open drawer holds the row it was handed, so a withdrawal or a new speaker has to be
// pointed at the refreshed one or it keeps showing the state it opened with.
async function refresh() {
	await myProposals.reload()
	const open = drawer.selected.value?.name
	const fresh = dated.value.find((proposal) => proposal.name === open)
	if (fresh) drawer.selected.value = fresh
}

// A proposal whose event was deleted has no date to file it under, so it drops out.
const dated = computed(() =>
	(myProposals.data || []).filter((proposal): proposal is ProposalWithEvent =>
		Boolean(proposal.start_date && proposal.event_title),
	),
)

// Plain dayjs: these are date-only values, and dayjsLocal shifts them a day back.
const months = computed(() =>
	groupEventsByMonth(inTab(dated.value, tab.value, dayjs().format("YYYY-MM-DD"))),
)

const emptyDescription = computed(() =>
	tab.value === "upcoming"
		? "Talks you propose will show up here."
		: "Talks you proposed for past events will show up here.",
)
</script>

<template>
	<CreateEventHeader />

	<TimelineList
		v-model:tab="tab"
		heading="Talk Proposals"
		icon="lucide-mic"
		noun="proposals"
		:months="months"
		:loading="myProposals.loading"
		:error="myProposals.error"
	>
		<template #empty-state>
			<EmptyState :title="`No ${tab} proposals`" :description="emptyDescription">
				<template #illustration>
					<Icon name="lucide-mic-off" class="size-8 text-ink-gray-4" />
				</template>
			</EmptyState>
		</template>

		<template #default="{ item }">
			<ProposalCard :proposal="item" @open="drawer.show(item)" />
		</template>
	</TimelineList>

	<ProposalDrawer
		v-model:open="drawer.open.value"
		:proposal="drawer.selected.value"
		@changed="refresh"
	/>
</template>
