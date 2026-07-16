<template>
	<div>
		<ListView
			v-if="proposals.data"
			:columns="columns"
			:rows="proposals.data"
			row-key="name"
			:options="{
				selectable: false,
				getRowRoute: (row: Record<string, any>) => ({
					name: 'proposal-details',
					params: { proposalId: row.name },
				}),
				emptyState: {
					title: __('No proposals yet'),
					description: __('Your talk proposals will appear here'),
				},
			}"
		>
			<template #cell="{ item, row, column }">
				<Badge
					v-if="column.key === 'status'"
					:theme="getStatusTheme(row.status)"
					variant="subtle"
					size="sm"
				>
					{{ item }}
				</Badge>
				<span v-else>{{ item }}</span>
			</template>
		</ListView>

		<div v-else-if="proposals.loading" class="w-4">
			<Spinner />
		</div>

		<div
			v-else-if="proposals.data && (proposals.data as any[]).length === 0"
			class="text-center py-8"
		>
			<div class="text-ink-gray-5 text-lg mb-2">
				{{ __("No proposals yet") }}
			</div>
			<div class="text-ink-gray-4 text-sm">
				{{ __("Your talk proposals will appear here") }}
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { session } from "@/data/session";
import { useProposalStatuses } from "@/composables/useProposalStatuses";
import { Badge, ListView, Spinner, dayjsLocal, useList } from "frappe-ui";

const { getStatusTheme } = useProposalStatuses();

const columns = [
	{ label: __("Title"), key: "title" },
	{ label: __("Event"), key: "event_title" },
	{ label: __("Status"), key: "status" },
	{ label: __("Submitted"), key: "formatted_creation" },
];

const proposals = useList({
	doctype: "Talk Proposal",
	fields: ["name", "title", "event.title as event_title", "status", "creation"],
	filters: {
		submitted_by: session.user,
	},
	orderBy: "creation desc",
	cacheKey: ["proposals-list", session.user],
	transform(data: any[]) {
		return data.map((proposal: Record<string, any>) => ({
			...proposal,
			formatted_creation: dayjsLocal(proposal.creation).format("MMM DD, YYYY"),
		}));
	},
});
</script>
