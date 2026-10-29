<script setup lang="ts">
import { Button, TextInput } from "frappe-ui"
import { nextTick, ref } from "vue"

import { useBoard, useBuilder } from "./useScheduleBoard"

const builder = useBuilder()
const board = useBoard()
const input = ref<{ el: HTMLInputElement | null } | null>(null)

function start() {
	board.roomDraft.value = ""
	board.addingRoom.value = true
	nextTick().then(() => input.value?.el?.focus())
}

async function submit() {
	const title = board.roomDraft.value.trim() || `Room ${builder.rooms.rooms.value.length + 1}`
	board.addingRoom.value = false
	board.roomDraft.value = ""
	await builder.rooms.add(title)
	builder.say(`Added ${title}`)
}
</script>

<template>
	<form v-if="board.addingRoom.value" class="w-full" @submit.prevent="submit">
		<TextInput ref="input" v-model="board.roomDraft.value" placeholder="Room name, then Enter" />
	</form>
	<Button v-else variant="ghost" iconLeft="lucide-plus" label="Add room" @click="start" />
</template>
