<script setup lang="ts">
import { Avatar, Badge, Icon, Tooltip, dayjsLocal } from "frappe-ui"

import EmptyState from "@/components/common/EmptyState.vue"
import type { CommunicationItem } from "@/types"
import { excerpt } from "@/utils/communicationText"

defineProps<{ communications: CommunicationItem[] }>()
const emit = defineEmits<{ open: [communication: CommunicationItem] }>()

const isScheduled = (row: CommunicationItem) =>
	!!row.scheduled_at && dayjsLocal(row.scheduled_at).isAfter(dayjsLocal())

// Scheduled rows say when they go out; sent rows say when they went.
const when = (row: CommunicationItem) =>
	isScheduled(row)
		? `Scheduled for ${dayjsLocal(row.scheduled_at as string).format("D MMM, h:mm A")}`
		: dayjsLocal(row.creation).fromNow()

const exact = (row: CommunicationItem) =>
	dayjsLocal(row.scheduled_at || row.creation).format("D MMM YYYY, h:mm A")
</script>

<template>
	<ul v-if="communications.length" class="divide-y divide-outline-gray-1">
		<li v-for="row in communications" :key="row.name">
			<button
				type="button"
				class="flex w-full items-center gap-3 px-2 py-3 text-left transition-colors duration-150 ease-out hover:bg-surface-gray-1 active:bg-surface-gray-2 motion-reduce:transition-none"
				:aria-label="`Open message ${row.subject || excerpt(row.message, 40)}`"
				@click="emit('open', row)"
			>
				<Avatar :label="row.sent_by" size="md" />

				<span class="flex min-w-0 flex-1 flex-col gap-0.5">
					<span class="truncate text-base font-medium text-ink-gray-8">
						{{ row.subject || excerpt(row.message) }}
					</span>
					<span class="flex items-center gap-1.5 text-sm text-ink-gray-5">
						<span class="truncate">{{ row.sent_by }}</span>
						<span aria-hidden="true">·</span>
						<Tooltip :text="exact(row)">
							<span :class="isScheduled(row) && 'text-ink-amber-5'">{{ when(row) }}</span>
						</Tooltip>
					</span>
				</span>

				<span class="flex shrink-0 items-center gap-1.5">
					<Badge variant="subtle" :label="`${row.recipient_count} ${row.audience.toLowerCase()}`" />
					<Badge v-if="isScheduled(row)" theme="amber" variant="subtle" label="Scheduled" />
				</span>
			</button>
		</li>
	</ul>
	<EmptyState
		v-else
		title="No announcements yet"
		description="Anything you send to this event's guests or speakers shows up here."
	>
		<template #illustration>
			<Icon name="lucide-megaphone" class="size-8 text-ink-gray-4" />
		</template>
	</EmptyState>
</template>
