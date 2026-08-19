<script setup lang="ts">
import TimelineList from "@/components/dashboard/TimelineList.vue";
import ProposalCard from "@/components/dashboard/proposals/ProposalCard.vue";
import { useMyProposals } from "@/data/proposals";
import type { ProposalWithEvent } from "@/types";
import { groupEventsByMonth } from "@/utils/eventGroups";
import { type TimelineTab, inTab } from "@/utils/timelineTabs";
import { dayjs } from "frappe-ui";
import { computed, ref } from "vue";

const tab = ref<TimelineTab>("upcoming");

const myProposals = useMyProposals();

// A proposal whose event was deleted has no date to file it under, so it drops out.
const dated = computed(() =>
	(myProposals.data || []).filter((proposal): proposal is ProposalWithEvent =>
		Boolean(proposal.start_date && proposal.event_title)
	)
);

// Plain dayjs: these are date-only values, and dayjsLocal shifts them a day back.
const months = computed(() =>
	groupEventsByMonth(inTab(dated.value, tab.value, dayjs().format("YYYY-MM-DD")))
);
</script>

<template>
	<TimelineList
		v-model:tab="tab"
		heading="Talk Proposals"
		noun="proposals"
		:months="months"
		:loading="myProposals.loading"
		:error="myProposals.error"
	>
		<template #default="{ item }">
			<ProposalCard :proposal="item" />
		</template>
	</TimelineList>
</template>
