<script setup lang="ts">
import { Button, TextInput } from "frappe-ui"
import { computed } from "vue"

import { useBoard, useBuilder } from "./useScheduleBoard"

const SUGGESTIONS = ["Main hall", "Hall B", "Workshop room", "Online"]
const builder = useBuilder()
const board = useBoard()

const suggestions = computed(() =>
	SUGGESTIONS.filter((name) => !builder.rooms.rooms.value.some((room) => room.title === name)),
)
const waiting = computed(() =>
	builder.talks.value.length
		? `${builder.talks.value.length} accepted talks are ready to place once rooms exist`
		: "Talks appear in the library once proposals are accepted",
)

async function add(title: string) {
	await builder.rooms.add(title)
	builder.say(`Added ${title}`)
}

async function submit() {
	const title = board.roomDraft.value.trim() || "Main hall"
	board.roomDraft.value = ""
	await add(title)
}
</script>

<template>
	<div class="absolute inset-0 z-[15] flex items-center justify-center bg-surface-base p-6">
		<div class="flex w-full max-w-[440px] flex-col gap-[18px]">
			<span
				class="flex size-10 items-center justify-center rounded-5 border border-outline-gray-2 text-ink-gray-7"
			>
				<span class="lucide-door-open size-[18px]" aria-hidden="true" />
			</span>
			<div>
				<div class="text-lg font-semibold text-ink-gray-9">Start with your rooms</div>
				<div class="mt-1.5 text-p-base leading-normal text-ink-gray-6 [text-wrap:pretty]">
					Each room or stage becomes a column. Add one to run a single track, or several for
					parallel sessions.
				</div>
			</div>
			<form class="flex gap-2" @submit.prevent="submit">
				<TextInput
					v-model="board.roomDraft.value"
					class="flex-1"
					size="md"
					placeholder="Room name, then Enter"
				/>
				<Button variant="solid" size="md" type="submit" label="Add room" />
			</form>
			<div class="flex flex-wrap items-center gap-1.5">
				<span class="mr-0.5 text-p-xs text-ink-gray-5">Suggestions</span>
				<Button
					v-for="name in suggestions"
					:key="name"
					variant="subtle"
					size="sm"
					iconLeft="lucide-plus"
					:label="name"
					@click="add(name)"
				/>
			</div>
			<div class="border-t border-outline-gray-1 pt-3.5 text-p-xs text-ink-gray-5">
				{{ waiting }}
			</div>
		</div>
	</div>
</template>
