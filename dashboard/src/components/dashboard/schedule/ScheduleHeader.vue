<script setup lang="ts">
import { useEventListener, useTimeAgo } from "@vueuse/core"
import { Button, toast, Tooltip } from "frappe-ui"
import { computed } from "vue"

import { useEventDoc } from "@/data/events"
import type { FrappeError } from "@/types"

import type { ScheduleBuilder } from "./useScheduleBuilder"

const props = defineProps<{ builder: ScheduleBuilder; eventId: string }>()

const event = useEventDoc(() => props.eventId)
const modified = useTimeAgo(() => props.builder.schedule.doc?.modified ?? "")
const previewUrl = computed(() =>
	event.doc?.route ? `${window.location.origin}/b/${event.doc.route}` : "",
)

const openPreview = () => window.open(previewUrl.value, "_blank")

const status = computed(() => {
	if (props.builder.dirty.value) return { label: "Unsaved", dot: "bg-surface-amber-5" }
	if (props.builder.isPublished.value) return { label: "Live", dot: "bg-surface-green-3" }
	return { label: "Draft", dot: "bg-surface-gray-4" }
})
const conflictCount = computed(() => props.builder.conflicts.value.size)
const saving = computed(() => props.builder.schedule.setValue.loading)

async function save(publish?: boolean) {
	try {
		await props.builder.save(publish)
		if (publish !== undefined)
			toast.success(publish ? "Schedule published" : "Schedule unpublished")
	} catch (error) {
		toast.error((error as FrappeError).message || "Could not save the schedule")
	}
}

useEventListener(window, "keydown", (keydown: KeyboardEvent) => {
	if (!(keydown.metaKey || keydown.ctrlKey) || keydown.key.toLowerCase() !== "s") return
	keydown.preventDefault()
	if (props.builder.dirty.value && !saving.value) save()
})
</script>

<template>
	<header
		class="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-outline-gray-1 bg-surface-base px-2.5"
	>
		<div class="flex min-w-0 items-center gap-2">
			<Tooltip text="Back to talks">
				<Button
					variant="ghost"
					icon="lucide-arrow-left"
					label="Back to talks"
					:route="{ name: 'event-talks', params: { eventId } }"
				/>
			</Tooltip>
			<div class="flex min-w-0 items-center gap-2 whitespace-nowrap text-p-sm">
				<span class="truncate text-ink-gray-5">{{ event.doc?.title }}</span>
				<span class="text-ink-gray-3" aria-hidden="true">/</span>
				<span class="font-medium text-ink-gray-9">Schedule</span>
				<span
					class="ml-1.5 flex items-center gap-1.5 rounded-full bg-surface-gray-2 px-2 py-0.5 text-p-xs text-ink-gray-6"
				>
					<span
						class="size-1.5 rounded-full transition-colors duration-200"
						:class="status.dot"
						aria-hidden="true"
					/>
					{{ status.label }}
				</span>
			</div>
		</div>

		<div class="flex items-center gap-2">
			<span
				v-if="conflictCount"
				class="rounded-full bg-surface-red-2 px-2 py-0.5 text-p-xs font-medium text-ink-red-6"
			>
				{{ conflictCount }} {{ conflictCount === 1 ? "conflict" : "conflicts" }}
			</span>
			<span
				v-if="builder.schedule.doc?.modified"
				class="hidden text-p-xs text-ink-gray-5 md:inline"
			>
				Modified {{ modified }}
			</span>
			<Button
				v-if="previewUrl"
				variant="subtle"
				iconLeft="lucide-eye"
				label="Preview"
				@click="openPreview"
			/>
			<Button
				v-if="builder.dirty.value"
				variant="subtle"
				label="Save"
				:loading="saving"
				@click="save()"
			/>
			<Button
				v-if="builder.isPublished.value"
				variant="ghost"
				label="Unpublish"
				:loading="saving"
				@click="save(false)"
			/>
			<Button
				v-else
				variant="solid"
				label="Publish schedule"
				:loading="saving"
				@click="save(true)"
			/>
		</div>
	</header>
</template>
