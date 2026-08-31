<script setup lang="ts">
import { Icon, dayjs } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import ProposalCard from "@/components/dashboard/proposals/ProposalCard.vue"
import TimelineList from "@/components/dashboard/TimelineList.vue"
import { useMyProposals } from "@/data/proposals"
import type { ProposalWithEvent } from "@/types"
import { groupEventsByMonth } from "@/utils/eventGroups"
import { type TimelineTab, inTab } from "@/utils/timelineTabs"

const tab = ref<TimelineTab>("upcoming")

const myProposals = useMyProposals()

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
			<ProposalCard :proposal="item" />
		</template>
	</TimelineList>
</template>
