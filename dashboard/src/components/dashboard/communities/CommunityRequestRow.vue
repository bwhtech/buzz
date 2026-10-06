<script setup lang="ts">
import { Avatar, dayjs } from "frappe-ui"

import type { CommunityRequest } from "@/types"

defineProps<{ request: CommunityRequest }>()
</script>

<template>
	<li class="flex items-center gap-3 py-3">
		<Avatar
			shape="square"
			size="lg"
			:image="request.event_team_logo ?? undefined"
			:label="request.event_team_name"
		/>
		<div class="min-w-0 flex-1 space-y-0.5">
			<a
				:href="`/events/${request.event_route}`"
				target="_blank"
				rel="noopener"
				class="block truncate text-base font-medium text-ink-gray-8 hover:underline"
			>
				{{ request.event_title }}
			</a>
			<p class="truncate text-sm text-ink-gray-5">
				<!-- Plain dayjs: a date-only value, which dayjsLocal shifts a day back. -->
				{{ dayjs(request.start_date).format("D MMM YYYY") }} · {{ request.event_team_name }}
				<template v-if="request.submitter_name"
					>· {{ __("by {0}", [request.submitter_name]) }}</template
				>
			</p>
		</div>
		<div class="flex shrink-0 gap-2"><slot /></div>
	</li>
</template>
