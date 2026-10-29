<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui"
import { ref, watch } from "vue"

import { dotClasses } from "./scheduleColors"
import type { ScheduleTrack } from "./scheduleTypes"

const props = defineProps<{ track: ScheduleTrack; count: number; canRemove: boolean }>()
const emit = defineEmits<{ rename: [title: string]; remove: [] }>()

const title = ref(props.track.title)
watch(
	() => props.track.title,
	(value) => (title.value = value),
)

function commit() {
	const trimmed = title.value.trim()
	if (!trimmed) title.value = props.track.title
	else if (trimmed !== props.track.title) emit("rename", trimmed)
}

const options = [
	{
		label: "Delete room",
		icon: "lucide-trash-2",
		theme: "red" as const,
		onClick: () => {
			const message = props.count
				? `Delete ${props.track.title} and its ${props.count} items?`
				: `Delete ${props.track.title}?`
			if (window.confirm(message)) emit("remove")
		},
	},
]
</script>

<template>
	<div class="flex items-center gap-2 px-3 py-2.5">
		<span
			class="size-2 shrink-0 rounded-full"
			:class="dotClasses(track.color)"
			aria-hidden="true"
		/>
		<div class="flex min-w-0 flex-1 flex-col">
			<input
				v-model="title"
				class="w-full truncate rounded-4 border-0 bg-transparent p-0 text-p-base font-semibold text-ink-gray-9 outline-none focus:bg-surface-gray-2 focus:px-1.5 focus:ring-0"
				:aria-label="`Room name, ${track.title}`"
				@blur="commit"
				@keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
			/>
			<span class="text-p-xs text-ink-gray-5"
				>{{ count }} {{ count === 1 ? "item" : "items" }}</span
			>
		</div>
		<Dropdown v-if="canRemove" :options="options" placement="right">
			<Button variant="ghost" icon="lucide-ellipsis" label="Room options" />
		</Dropdown>
	</div>
</template>
