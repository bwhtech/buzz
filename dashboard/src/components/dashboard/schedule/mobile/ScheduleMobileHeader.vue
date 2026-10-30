<script setup lang="ts">
import { Button, Dropdown, toast } from "frappe-ui"
import { computed } from "vue"

import { useEventDoc } from "@/data/events"
import type { FrappeError } from "@/types"
import { openEventSchedule } from "@/utils/eventUrl"

import { useBuilder } from "../useScheduleBoard"

const props = defineProps<{ eventId: string }>()
const builder = useBuilder()
const event = useEventDoc(() => props.eventId)

const published = builder.isPublished
const saving = computed(() => builder.saveState.value === "saving")
const editedLive = computed(() => published.value && builder.dirty.value)
const status = computed(() => {
	if (!published.value) return { label: "Draft", dot: "bg-surface-gray-4" }
	if (editedLive.value) return { label: "Edited", dot: "bg-surface-amber-5" }
	return { label: "Live", dot: "bg-surface-green-3" }
})
const route = computed(() => event.doc?.route)

function save(publish: boolean) {
	builder
		.save(publish)
		.then(() => toast.success(publish ? "Schedule published" : "Schedule unpublished"))
		.catch((error: FrappeError) => toast.error(error.message || "Could not save the schedule"))
}
</script>

<template>
	<header
		class="box-content grid h-[52px] shrink-0 grid-cols-[44px_minmax(0,1fr)_auto] items-center gap-1 bg-surface-base pl-1.5 pr-2.5 pt-[env(safe-area-inset-top)]"
	>
		<Button
			variant="ghost"
			size="lg"
			icon="lucide-chevron-left"
			label="Back to talks"
			:route="{ name: 'event-talks', params: { eventId } }"
		/>
		<div class="flex min-w-0 flex-col gap-0.5">
			<span class="truncate text-[15px] font-semibold text-ink-gray-9">Schedule</span>
			<span class="flex items-center gap-1.5 whitespace-nowrap text-p-xs text-ink-gray-5">
				<span class="size-1.5 shrink-0 rounded-full" :class="status.dot" aria-hidden="true" />
				<span class="truncate">{{ status.label }} · {{ event.doc?.title }}</span>
			</span>
		</div>
		<div class="flex items-center gap-1">
			<Button
				v-if="builder.canUndo.value"
				variant="ghost"
				size="lg"
				icon="lucide-undo-2"
				label="Undo"
				@click="builder.undo"
			/>
			<Button
				v-if="route"
				variant="ghost"
				size="lg"
				icon="lucide-arrow-up-right"
				label="View schedule page"
				@click="openEventSchedule(route)"
			/>
			<Dropdown
				v-if="published && !builder.dirty.value"
				align="end"
				:options="[{ label: 'Unpublish', icon: 'lucide-eye-off', onClick: () => save(false) }]"
			>
				<Button variant="ghost" size="lg" icon="lucide-ellipsis" label="Publishing options" />
			</Dropdown>
			<Button
				v-else
				variant="solid"
				size="lg"
				:label="published ? 'Save and publish' : 'Publish'"
				:loading="saving"
				@click="save(true)"
			/>
		</div>
	</header>
</template>
