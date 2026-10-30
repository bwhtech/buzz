<script setup lang="ts">
import { Button, Dropdown, TextInput, toast } from "frappe-ui"
import { computed, nextTick, ref, watch } from "vue"

import type { FrappeError } from "@/types"

import { dotColor } from "./scheduleColors"
import type { ScheduleTrack } from "./scheduleTypes"
import { useBoard, useBuilder } from "./useScheduleBoard"

const props = defineProps<{ track: ScheduleTrack; index: number; count: number; total: number }>()
const builder = useBuilder()
const board = useBoard()

const renaming = computed(() => board.renamingTrack.value === props.track.name)
const input = ref<{ el: HTMLInputElement | null } | null>(null)
watch(renaming, (on) => on && nextTick().then(() => input.value?.el?.focus()))

const meta = computed(() => {
	const seats = props.track.capacity
		? `${props.track.capacity.toLocaleString("en-US")} seats · `
		: ""
	return `${seats}${props.count} ${props.count === 1 ? "item" : "items"}`
})

const withErrorToast = (action: Promise<unknown>) =>
	action.catch((error: FrappeError) => toast.error(error.message || "Could not change the track"))

function remove() {
	const message = `Delete ${props.track.title}? Its items on every day are deleted with it.`
	if (window.confirm(message)) withErrorToast(builder.removeTrack(props.track.name))
}

function startRename() {
	board.trackDraft.value = props.track.title
	board.renamingTrack.value = props.track.name
}

async function submitRename() {
	if (!renaming.value) return
	const title = board.trackDraft.value.trim()
	board.renamingTrack.value = null
	if (!title || title === props.track.title) return
	await withErrorToast(builder.renameTrack(props.track.name, title))
}

const options = computed(() => [
	{ label: "Rename", icon: "lucide-pen-line", onClick: startRename },
	{
		label: "Move left",
		icon: "lucide-arrow-left",
		disabled: props.index === 0,
		onClick: () => withErrorToast(builder.moveTrack(props.track.name, -1)),
	},
	{
		label: "Move right",
		icon: "lucide-arrow-right",
		disabled: props.index === props.total - 1,
		onClick: () => withErrorToast(builder.moveTrack(props.track.name, 1)),
	},
	{
		label: "Delete track",
		icon: "lucide-trash-2",
		theme: "red" as const,
		disabled: props.total === 1,
		onClick: remove,
	},
])
</script>

<template>
	<div class="flex min-w-0 items-center gap-2 px-3 py-2">
		<span
			class="size-2 shrink-0 rounded-full"
			:style="{ background: dotColor(track.color) }"
			aria-hidden="true"
		/>
		<form v-if="renaming" class="min-w-0 flex-1" @submit.prevent="submitRename">
			<TextInput ref="input" v-model="board.trackDraft.value" @blur="submitRename" />
		</form>
		<div v-else class="min-w-0 flex-1">
			<div class="truncate text-p-sm font-semibold text-ink-gray-9">{{ track.title }}</div>
			<div class="truncate text-p-xs text-ink-gray-5">{{ meta }}</div>
		</div>
		<Dropdown :options="options" placement="right">
			<Button variant="ghost" size="sm" icon="lucide-ellipsis" label="Track options" />
		</Dropdown>
	</div>
</template>
