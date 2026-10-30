<script setup lang="ts">
import { Button, Dropdown, TextInput } from "frappe-ui"
import { computed, nextTick, ref, watch } from "vue"

import { dotColor } from "./scheduleColors"
import type { ScheduleRoom } from "./scheduleTypes"
import { useBoard, useBuilder } from "./useScheduleBoard"

const props = defineProps<{ room: ScheduleRoom; index: number; count: number; total: number }>()
const builder = useBuilder()
const board = useBoard()

const renaming = computed(() => board.renamingRoom.value === props.room.name)
const input = ref<{ el: HTMLInputElement | null } | null>(null)
watch(renaming, (on) => on && nextTick().then(() => input.value?.el?.focus()))

const meta = computed(() => {
	const seats = props.room.capacity ? `${props.room.capacity.toLocaleString("en-US")} seats · ` : ""
	return `${seats}${props.count} ${props.count === 1 ? "item" : "items"}`
})

function startRename() {
	board.roomDraft.value = props.room.title
	board.renamingRoom.value = props.room.name
}

async function submitRename() {
	const title = board.roomDraft.value.trim()
	board.renamingRoom.value = null
	if (!title || title === props.room.title) return
	await builder.rooms.rename(props.room.name, title)
	await builder.rooms.reload()
}

const options = computed(() => [
	{ label: "Rename", icon: "lucide-pen-line", onClick: startRename },
	{
		label: "Move left",
		icon: "lucide-arrow-left",
		disabled: props.index === 0,
		onClick: () => builder.rooms.move(props.room.name, -1),
	},
	{
		label: "Move right",
		icon: "lucide-arrow-right",
		disabled: props.index === props.total - 1,
		onClick: () => builder.rooms.move(props.room.name, 1),
	},
	{
		label: "Delete room",
		icon: "lucide-trash-2",
		theme: "red" as const,
		disabled: props.total === 1,
		onClick: () => builder.removeRoom(props.room.name),
	},
])
</script>

<template>
	<div class="flex min-w-0 items-center gap-2 px-3 py-2">
		<span
			class="size-2 shrink-0 rounded-full"
			:style="{ background: dotColor(room.color) }"
			aria-hidden="true"
		/>
		<form v-if="renaming" class="min-w-0 flex-1" @submit.prevent="submitRename">
			<TextInput ref="input" v-model="board.roomDraft.value" @blur="submitRename" />
		</form>
		<div v-else class="min-w-0 flex-1">
			<div class="truncate text-p-sm font-semibold text-ink-gray-9">{{ room.title }}</div>
			<div class="truncate text-p-xs text-ink-gray-5">{{ meta }}</div>
		</div>
		<Dropdown :options="options" placement="right">
			<Button variant="ghost" size="sm" icon="lucide-ellipsis" label="Room options" />
		</Dropdown>
	</div>
</template>
