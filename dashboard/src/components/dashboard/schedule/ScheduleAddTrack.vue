<script setup lang="ts">
import { Button, TextInput, toast } from "frappe-ui"
import { nextTick, ref } from "vue"

import { useBoard, useBuilder } from "./useScheduleBoard"

const builder = useBuilder()
const board = useBoard()
const input = ref<{ el: HTMLInputElement | null } | null>(null)

function start() {
	board.trackDraft.value = ""
	board.addingTrack.value = true
	nextTick().then(() => input.value?.el?.focus())
}

async function submit() {
	const title = board.trackDraft.value.trim() || `Track ${builder.tracks.tracks.value.length + 1}`
	board.addingTrack.value = false
	board.trackDraft.value = ""
	await builder.tracks
		.add(title)
		.then(() => builder.showToast(`Added ${title}`))
		.catch(() => toast.error("Could not add the track"))
}
</script>

<template>
	<form v-if="board.addingTrack.value" class="w-full" @submit.prevent="submit">
		<TextInput ref="input" v-model="board.trackDraft.value" placeholder="Track name, then Enter" />
	</form>
	<Button v-else variant="ghost" iconLeft="lucide-plus" label="Add track" @click="start" />
</template>
