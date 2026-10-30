<script setup lang="ts">
import { TextInput } from "frappe-ui"
import { computed, nextTick, ref, watch } from "vue"

import { dotColor } from "./scheduleColors"
import { scheduleIcon } from "./scheduleIcons"
import { TALK_TYPES, clock, speakerLine } from "./scheduleLayout"
import { useBoard, useBuilder } from "./useScheduleBoard"

const builder = useBuilder()
const board = useBoard()
const search = ref("")
const box = ref<HTMLElement | null>(null)
const quick = board.quick

watch(quick, (open) => {
	if (!open) return
	search.value = ""
	nextTick().then(() => box.value?.querySelector("input")?.focus())
})

const query = computed(() => search.value.trim().toLowerCase())
const talks = computed(() =>
	builder.unscheduledTalks.value
		.filter((talk) =>
			`${talk.title} ${talk.speakers.join(" ")}`.toLowerCase().includes(query.value),
		)
		.slice(0, 6),
)
const templates = computed(() =>
	builder.types.value.filter(
		(type) => !TALK_TYPES.has(type.name) && type.title.toLowerCase().includes(query.value),
	),
)
const title = computed(() =>
	quick.value
		? `Add to ${builder.rooms.titleOf(quick.value.room)} at ${clock(quick.value.start)}`
		: "",
)
const style = computed(() => {
	if (!quick.value) return {}
	const { x, y } = quick.value
	return {
		left: `${Math.min(x + 8, window.innerWidth - 336)}px`,
		top: `${Math.max(8, Math.min(y - 20, window.innerHeight - 440))}px`,
	}
})

function pick(kind: "talk" | "type", id: string) {
	if (!quick.value) return
	const item = builder.place(
		{ kind, id },
		builder.activeDate.value,
		quick.value.room,
		quick.value.start,
	)
	if (item && item.type === "Custom") board.select(item.key)
	quick.value = null
	board.ghost.value = null
}
function close() {
	quick.value = null
	board.ghost.value = null
}
</script>

<template>
	<template v-if="quick">
		<div class="fixed inset-0 z-40" @click="close" />
		<div
			ref="box"
			class="fixed z-[41] flex max-h-[420px] w-80 origin-top-left flex-col overflow-hidden rounded-6 border border-outline-gray-1 bg-surface-elevation-2 shadow-2xl"
			:style="style"
		>
			<div class="px-3 pb-1.5 pt-2.5 text-p-xs text-ink-gray-5">{{ title }}</div>
			<div class="px-2 pb-1.5">
				<TextInput
					v-model="search"
					placeholder="Find a talk or item"
					autocomplete="off"
					@keydown.esc="close"
				>
					<template #prefix
						><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
					/></template>
				</TextInput>
			</div>
			<div class="min-h-0 flex-1 overflow-auto px-1.5 pb-1.5">
				<div class="px-2 py-1.5 text-p-xs font-medium text-ink-gray-5">Unscheduled talks</div>
				<button
					v-for="talk in talks"
					:key="talk.name"
					type="button"
					class="flex w-full items-start gap-2 rounded-4 px-2 py-1.5 text-left hover:bg-surface-gray-2"
					@click="pick('talk', talk.name)"
				>
					<span
						class="mt-1.5 size-2 shrink-0 rounded-full"
						:style="{ background: dotColor(builder.typesByName.value.Talk?.color) }"
					/>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-p-sm text-ink-gray-9">{{ talk.title }}</span>
						<span class="block text-p-xs text-ink-gray-5"
							>{{ speakerLine(talk.speakers) }} · {{ builder.talkDuration.value }} min</span
						>
					</span>
				</button>
				<div v-if="!talks.length" class="px-2 pb-2 text-p-xs text-ink-gray-5">
					No unscheduled talks match
				</div>
				<div
					class="mt-1 border-t border-outline-gray-1 px-2 pb-1.5 pt-2 text-p-xs font-medium text-ink-gray-5"
				>
					Custom items
				</div>
				<button
					v-for="type in templates"
					:key="type.name"
					type="button"
					class="flex w-full items-center gap-2 rounded-4 px-2 py-1.5 text-left hover:bg-surface-gray-2"
					@click="pick('type', type.name)"
				>
					<span :class="[scheduleIcon(type.icon), 'size-4 text-ink-gray-6']" aria-hidden="true" />
					<span class="flex-1 text-p-sm text-ink-gray-9">{{
						type.name === "Custom" ? "Untitled item" : type.title
					}}</span>
					<span class="text-p-xs text-ink-gray-5">{{ type.default_duration }} min</span>
				</button>
			</div>
		</div>
	</template>
</template>
