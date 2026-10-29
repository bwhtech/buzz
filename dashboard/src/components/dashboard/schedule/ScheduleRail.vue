<script setup lang="ts">
import { Button, FormControl } from "frappe-ui"
import { computed, ref } from "vue"

import { scheduleIcon } from "./scheduleIcons"
import { defaultMinutes, durationLabel } from "./scheduleTime"
import { DRAG_TYPE, type ScheduleItemType, type ScheduleTalk } from "./scheduleTypes"

const props = defineProps<{ talks: ScheduleTalk[]; types: ScheduleItemType[]; dayLabel: string }>()
const emit = defineEmits<{
	addTalk: [talk: ScheduleTalk]
	addType: [type: ScheduleItemType]
	createType: [title: string]
}>()

const search = ref("")
const matches = computed(() => {
	const query = search.value.trim().toLowerCase()
	return props.talks.filter((talk) =>
		`${talk.title} ${talk.speakers}`.toLowerCase().includes(query),
	)
})
const customTypes = computed(() => props.types.filter((type) => type.name !== "Talk"))

const newTitle = ref("")
function createType() {
	const title = newTitle.value.trim()
	if (!title) return
	emit("createType", title)
	newTitle.value = ""
}

function drag(event: DragEvent, payload: object) {
	event.dataTransfer?.setData(DRAG_TYPE, JSON.stringify(payload))
	if (event.dataTransfer) event.dataTransfer.effectAllowed = "copy"
}
</script>

<template>
	<aside class="flex h-full w-80 shrink-0 flex-col border-l border-outline-gray-1 bg-surface-base">
		<section class="flex min-h-0 flex-1 flex-col gap-3 p-4">
			<div class="flex items-center justify-between">
				<h2 class="text-p-base font-semibold text-ink-gray-9">Unscheduled talks</h2>
				<span class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-p-xs text-ink-gray-6">
					{{ talks.length }}
				</span>
			</div>
			<FormControl v-model="search" type="text" placeholder="Search talks" autocomplete="off" />
			<p v-if="!talks.length" class="text-p-sm text-ink-gray-5">
				Every accepted talk is on the schedule.
			</p>
			<ul class="-mx-1 flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto px-1">
				<li v-for="talk in matches" :key="talk.name">
					<button
						type="button"
						draggable="true"
						class="flex w-full cursor-grab flex-col items-start gap-0.5 rounded-5 border border-outline-blue-1 bg-surface-blue-1 px-3 py-2 text-left transition-transform duration-150 ease-out active:scale-[0.98]"
						@dragstart="drag($event, { kind: 'talk', name: talk.name })"
						@click="emit('addTalk', talk)"
					>
						<span class="text-p-sm font-semibold text-ink-blue-7">{{ talk.title }}</span>
						<span v-if="talk.speakers" class="text-p-xs text-ink-gray-6">{{ talk.speakers }}</span>
					</button>
				</li>
			</ul>
			<p v-if="talks.length" class="text-p-xs text-ink-gray-5">
				Drag a talk onto a room, or click to add it to {{ dayLabel }} at the next free slot.
			</p>
		</section>

		<section class="flex max-h-[45%] flex-col gap-3 border-t border-outline-gray-1 p-4">
			<h2 class="text-p-base font-semibold text-ink-gray-9">Custom items</h2>
			<ul class="-mx-1 flex min-h-0 flex-col gap-1 overflow-y-auto px-1">
				<li v-for="type in customTypes" :key="type.name">
					<button
						type="button"
						draggable="true"
						class="flex w-full cursor-grab items-center gap-2.5 rounded-5 px-2 py-1.5 text-left transition-[background-color,transform] duration-150 ease-out hover:bg-surface-gray-2 active:scale-[0.98]"
						@dragstart="drag($event, { kind: 'type', name: type.name })"
						@click="emit('addType', type)"
					>
						<span
							:class="[scheduleIcon(type.icon), 'size-4 shrink-0 text-ink-gray-6']"
							aria-hidden="true"
						/>
						<span class="min-w-0 flex-1 truncate text-p-sm text-ink-gray-9">{{ type.title }}</span>
						<span class="text-p-xs text-ink-gray-5">
							{{ durationLabel(defaultMinutes(type.name)) }}
						</span>
					</button>
				</li>
			</ul>
			<form class="flex items-center gap-2" @submit.prevent="createType">
				<FormControl
					v-model="newTitle"
					class="flex-1"
					type="text"
					placeholder="New item type, e.g. Panel"
					autocomplete="off"
				/>
				<Button type="submit" variant="subtle" icon="lucide-plus" label="Create item type" />
			</form>
		</section>
	</aside>
</template>
