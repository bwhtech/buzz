<script setup lang="ts">
import { useEventListener, useTimeAgo } from "@vueuse/core"
import { Badge, Button, Tooltip } from "frappe-ui"
import { computed } from "vue"

import { useEventDoc } from "@/data/events"
import { openEventSchedule } from "@/utils/eventUrl"

import { useBoard, useBuilder } from "./useScheduleBoard"

const props = defineProps<{ eventId: string }>()
const builder = useBuilder()
const board = useBoard()
const event = useEventDoc(() => props.eventId)

const modified = useTimeAgo(() => builder.schedule.doc?.modified ?? "")
const route = computed(() => event.doc?.route)
const published = builder.isPublished
const saving = computed(() => builder.saveState.value === "saving")
const conflicts = computed(() => builder.conflictedItems.value.length)
const conflictIndex = computed(() =>
	builder.conflictedItems.value.findIndex((item) => item.key === board.selectedKey.value),
)
const conflictLabel = computed(() => {
	if (conflictIndex.value !== -1)
		return `${conflictIndex.value + 1} of ${conflicts.value} conflicts`
	return `${conflicts.value} ${conflicts.value === 1 ? "conflict" : "conflicts"}`
})
const unpublishedChanges = computed(() => published.value && builder.dirty.value)

const status = computed(() => {
	const state = builder.saveState.value
	if (state === "saving") return "Saving…"
	if (state === "error") return "Couldn't save"
	if (unpublishedChanges.value) return "Unpublished changes"
	if (builder.dirty.value) return "Saving soon…"
	return `Saved ${modified.value}`
})

const save = builder.saveWithToast

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
		<div
			v-if="conflicts"
			class="flex h-7 shrink-0 items-center overflow-hidden rounded-4 bg-surface-red-1 text-p-sm text-ink-red-7"
		>
			<button
				type="button"
				class="flex h-full items-center gap-1.5 px-2 tabular-nums hover:bg-surface-red-2"
				@click="board.stepConflict(1)"
			>
				<span class="lucide-triangle-alert size-3.5" aria-hidden="true" />{{ conflictLabel }}
			</button>
			<button
				type="button"
				class="grid h-full w-6 place-items-center hover:bg-surface-red-2"
				aria-label="Previous conflict"
				title="Previous conflict"
				@click="board.stepConflict(-1)"
			>
				<span class="lucide-chevron-up size-3.5" aria-hidden="true" />
			</button>
			<button
				type="button"
				class="grid h-full w-6 place-items-center hover:bg-surface-red-2"
				aria-label="Next conflict"
				title="Next conflict"
				@click="board.stepConflict(1)"
			>
				<span class="lucide-chevron-down size-3.5" aria-hidden="true" />
			</button>
		</div>
		<span
			class="hidden min-w-0 items-center gap-1.5 truncate text-p-sm md:flex"
			:class="unpublishedChanges ? 'text-ink-amber-7' : 'text-ink-gray-5'"
			aria-live="polite"
		>
			<span
				v-if="unpublishedChanges"
				class="size-1.5 shrink-0 rounded-full bg-current"
				aria-hidden="true"
			/>
			<span>{{ status }}</span>
		</span>
		<Tooltip v-if="route" text="View schedule page">
			<Button
				variant="ghost"
				icon="lucide-arrow-up-right"
				label="View schedule page"
				@click="openEventSchedule(route)"
			/>
		</Tooltip>
		<template v-if="published">
			<Button
				v-if="builder.dirty.value"
				variant="solid"
				label="Save and publish"
				:loading="saving"
				@click="save(true)"
			/>
			<Button v-else variant="ghost" label="Unpublish" :loading="saving" @click="save(false)" />
		</template>
		<template v-else>
			<Button
				v-if="builder.dirty.value"
				variant="subtle"
				label="Save"
				:loading="saving"
				@click="save()"
			/>
			<Button variant="solid" label="Publish" :loading="saving" @click="save(true)" />
		</template>
	</header>
</template>
