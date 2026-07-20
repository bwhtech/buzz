<template>
	<div>
		<ListView
			v-if="proposals.data"
			:columns="columns"
			:rows="proposals.data"
			row-key="name"
			:options="{
				selectable: false,
				getRowRoute: (row) => ({
					name: 'proposal-details',
					params: { proposalId: row.name },
				}),
				emptyState: {
					title: __('No proposals yet'),
					description: __('Your talk proposals will appear here'),
				},
			}"
		>
			<template #cell="{ item, row, column, align }">
				<Badge
					v-if="column.key === 'status'"
					:theme="getStatusTheme(row.status)"
					variant="subtle"
					size="sm"
				>
					{{ item }}
				</Badge>
				<ListRowItem v-else :column="column" :row="row" :item="item" :align="align" />
			</template>
		</ListView>

		<div v-else-if="proposals.loading" class="w-4">
			<Spinner />
		</div>

		<div v-else-if="proposals.data && proposals.data.length === 0" class="text-center py-8">
			<div class="text-ink-gray-5 text-lg mb-2">
				{{ __("No proposals yet") }}
			</div>
			<div class="text-ink-gray-4 text-sm">
				{{ __("Your talk proposals will appear here") }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { session } from "@/data/session";
import { useProposalStatuses } from "@/composables/useProposalStatuses";
import { Badge, ListRowItem, ListView, Spinner, dayjsLocal, useList } from "frappe-ui";

const { getStatusTheme } = useProposalStatuses();

const columns = [
	{ label: __("Title"), key: "title", width: "240px" },
	{ label: __("Event"), key: "event_title", width: "180px" },
	{ label: __("Status"), key: "status", width: "130px" },
	{ label: __("Submitted"), key: "formatted_creation", width: "120px" },
];

const proposals = useList({
	doctype: "Talk Proposal",
	fields: ["name", "title", "event.title as event_title", "status", "creation"],
	filters: {
		submitted_by: session.user,
	},
	orderBy: "creation desc",
	auto: true,
	cacheKey: ["proposals-list", session.user],
	transform(data) {
		return data.map((proposal) => ({
			...proposal,
			formatted_creation: dayjsLocal(proposal.creation).format("MMM DD, YYYY"),
		}));
	},
});
</script>
