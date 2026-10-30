<script setup lang="ts">
import { Badge, Button, toast } from "frappe-ui"
import { computed } from "vue"

import { useEventDoc } from "@/data/events"
import type { FrappeError } from "@/types"

import { useBuilder } from "../useScheduleBoard"

const props = defineProps<{ eventId: string }>()
const builder = useBuilder()
const event = useEventDoc(() => props.eventId)

const published = builder.isPublished
const saving = computed(() => builder.saveState.value === "saving")
const publishable = computed(() => !published.value || builder.dirty.value)

function publish() {
	builder
		.save(true)
		.then(() => toast.success("Schedule published"))
		.catch((error: FrappeError) => toast.error(error.message || "Could not save the schedule"))
}
</script>

<template>
	<header
		class="flex h-[52px] shrink-0 items-center gap-1 border-b border-outline-gray-1 px-2.5 pt-[env(safe-area-inset-top)] box-content"
	>
		<Button
			variant="ghost"
			icon="lucide-chevron-left"
			label="Back to talks"
			:route="{ name: 'event-talks', params: { eventId } }"
		/>
		<div class="min-w-0 flex-1 truncate text-center text-lg font-semibold text-ink-gray-9">
			{{ event.doc?.title }}
		</div>
		<Button variant="ghost" icon="lucide-undo-2" label="Undo" @click="builder.undo" />
		<Button
			v-if="publishable"
			variant="solid"
			size="sm"
			:label="published ? 'Save and publish' : 'Publish'"
			:loading="saving"
			@click="publish"
		/>
		<Badge v-else label="Live" theme="green" />
	</header>
</template>
