<template>
	<div>
		<ListView
			v-if="sponsorships.data"
			:columns="columns"
			:rows="sponsorships.data"
			row-key="name"
			:options="{
				selectable: false,
				getRowRoute: (row: Record<string, any>) => ({
					name: 'sponsorship-details',
					params: { enquiryId: row.name },
				}),
				emptyState: {
					title: __('No sponsorship inquiries yet'),
					description: __('Your sponsorship inquiries will appear here'),
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
				<Badge
					v-else-if="column.key === 'sponsorship_status'"
					:theme="row.has_sponsor ? 'green' : 'gray'"
					variant="subtle"
					size="sm"
				>
					{{ row.has_sponsor ? __("Sponsored") : __("Inquiry Only") }}
				</Badge>
				<span v-else>{{ item }}</span>
			</template>
		</ListView>

		<div v-else-if="sponsorships.loading" class="w-4">
			<Spinner />
		</div>

		<div
			v-else-if="sponsorships.data && sponsorships.data.length === 0"
			class="text-center py-8"
		>
			<div class="text-ink-gray-5 text-lg mb-2">
				{{ __("No sponsorship inquiries yet") }}
			</div>
			<div class="text-ink-gray-4 text-sm">
				{{ __("Your sponsorship inquiries will appear here") }}
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Badge, ListView, Spinner, createResource } from "frappe-ui";
import { dayjsLocal } from "frappe-ui";

const columns = [
	{ label: __("Company"), key: "company_name" },
	{ label: __("Event"), key: "event_title" },
	{ label: __("Tier"), key: "tier_title" },
	{ label: __("Status"), key: "status" },
	{ label: __("Sponsorship"), key: "sponsorship_status" },
	{ label: __("Submitted"), key: "formatted_creation" },
];

const sponsorships = createResource({
	url: "buzz.api.get_user_sponsorship_inquiries",
	auto: true,
	cacheKey: "sponsorships-list",
	onError: console.error,
	transform(data: any[]) {
		return data.map((inquiry: Record<string, any>) => ({
			...inquiry,
			formatted_creation: dayjsLocal(inquiry.creation).format("MMM DD, YYYY"),
			sponsorship_status: inquiry.has_sponsor ? __("Sponsored") : __("Inquiry Only"),
		}));
	},
});

const getStatusTheme = (status: string) => {
	switch (status) {
		case "Paid":
			return "green";
		case "Payment Pending":
			return "orange";
		case "Approval Pending":
			return "blue";
		case "Withdrawn":
			return "red";
		default:
			return "gray";
	}
};
</script>
