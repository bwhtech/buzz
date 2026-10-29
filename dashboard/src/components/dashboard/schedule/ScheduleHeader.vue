<script setup lang="ts">
import { useEventListener, useTimeAgo } from "@vueuse/core"
import { Badge, Button, toast, Tooltip } from "frappe-ui"
import { computed } from "vue"

import { useEventDoc } from "@/data/events"
import type { FrappeError } from "@/types"

import { useBuilder } from "./useScheduleBoard"

const props = defineProps<{ eventId: string }>()
const builder = useBuilder()
const event = useEventDoc(() => props.eventId)

const modified = useTimeAgo(() => builder.schedule.doc?.modified ?? "")
const previewUrl = computed(() =>
	event.doc?.route ? `${window.location.origin}/events/${event.doc.route}/schedule` : "",
)
const published = builder.isPublished
const saving = computed(() => builder.saveState.value === "saving")
const conflicts = computed(() => builder.conflictCount.value)

const status = computed(() => {
	const state = builder.saveState.value
	if (state === "saving") return "Saving…"
	if (state === "error") return "Couldn't save"
	if (builder.dirty.value) return published.value ? "Unpublished changes" : "Saving soon…"
	return `Saved ${modified.value}`
})

async function save(publish?: boolean) {
	try {
		await builder.save(publish)
		if (publish !== undefined)
			toast.success(publish ? "Schedule published" : "Schedule unpublished")
	} catch (error) {
		toast.error((error as FrappeError).message || "Could not save the schedule")
	}
}

useEventListener(window, "keydown", (keydown: KeyboardEvent) => {
	if (!(keydown.metaKey || keydown.ctrlKey) || keydown.key.toLowerCase() !== "s") return
	keydown.preventDefault()
	if (builder.dirty.value && !saving.value) save()
})
</script>

<template>
	<header class="flex h-[52px] shrink-0 items-center gap-3 pl-3 pr-4">
		<Tooltip text="Back to talks">
			<Button
				variant="ghost"
				icon="lucide-arrow-left"
				label="Back to talks"
				:route="{ name: 'event-talks', params: { eventId } }"
			/>
		</Tooltip>
		<div class="flex min-w-0 shrink-0 items-center gap-1.5 whitespace-nowrap text-base">
			<span class="truncate text-ink-gray-5">{{ event.doc?.title }}</span>
			<span class="text-ink-gray-4" aria-hidden="true">/</span>
			<span class="font-medium text-ink-gray-9">Schedule</span>
		</div>
		<Badge :label="published ? 'Live' : 'Draft'" :theme="published ? 'green' : 'gray'" />
		<div class="min-w-0 flex-1" />
		<Badge
			v-if="conflicts"
			:label="`${conflicts} ${conflicts === 1 ? 'conflict' : 'conflicts'}`"
			theme="red"
		/>
		<span class="hidden min-w-0 truncate text-p-sm text-ink-gray-5 md:inline" aria-live="polite">{{
			status
		}}</span>
		<Button
			v-if="previewUrl"
			variant="subtle"
			iconLeft="lucide-eye"
			label="Preview"
			:link="previewUrl"
		/>
		<Button
			v-if="published"
			variant="ghost"
			label="Unpublish"
			:loading="saving"
			@click="save(false)"
		/>
		<Button
			v-if="!published || builder.dirty.value"
			variant="solid"
			:label="published ? 'Publish changes' : 'Publish schedule'"
			:loading="saving"
			@click="save(true)"
		/>
	</header>
</template>
