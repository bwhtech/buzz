<script setup lang="ts">
import { Badge, Button, TextInput } from "frappe-ui"
import { computed, ref } from "vue"

import { badgeTheme } from "./scheduleColors"
import { speakerLine } from "./scheduleLayout"
import { useBoard, useBuilder } from "./useScheduleBoard"

const builder = useBuilder()
const board = useBoard()
const search = ref("")

const talkType = computed(() => builder.typesByName.value.Talk)
const duration = computed(() => talkType.value?.default_duration ?? 30)
const scheduled = computed(() => new Set(builder.items.value.map((item) => item.talk)))

const matching = computed(() => {
	const query = search.value.trim().toLowerCase()
	return builder.talks.value.filter((talk) =>
		`${talk.title} ${talk.speakers.join(" ")}`.toLowerCase().includes(query),
	)
})
const unscheduled = computed(() => matching.value.filter((talk) => !scheduled.value.has(talk.name)))

const drag = (name: string, event: DragEvent) =>
	board.startDrag(
		{ kind: "talk", id: name, duration: duration.value, span: false, grabX: 0, grabY: 0 },
		event,
	)
const add = (name: string) => builder.place({ kind: "talk", id: name }, builder.activeDate.value)
</script>

<template>
	<div class="flex min-h-0 flex-1 flex-col">
		<div class="px-3 pb-2">
			<TextInput v-model="search" placeholder="Search talks or speakers" autocomplete="off">
				<template #prefix
					><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
				/></template>
			</TextInput>
		</div>
		<div class="flex min-h-0 flex-1 flex-col gap-2 overflow-auto px-3 pb-4 pt-1">
			<div class="flex justify-between px-0.5 pt-1 text-p-xs text-ink-gray-5">
				<span>Unscheduled</span><span>{{ unscheduled.length }}</span>
			</div>
			<div
				v-for="talk in unscheduled"
				:key="talk.name"
				draggable="true"
				class="flex cursor-grab gap-1 rounded-5 border border-outline-gray-2 bg-surface-base p-2.5 pl-1.5 transition-shadow hover:border-outline-gray-3 hover:shadow-sm"
				@dragstart="drag(talk.name, $event)"
				@dragend="board.endDrag"
			>
				<span
					class="lucide-grip-vertical mt-0.5 size-3.5 shrink-0 text-ink-gray-4"
					aria-hidden="true"
				/>
				<div class="flex min-w-0 flex-1 flex-col gap-0.5">
					<div
						class="text-p-sm font-semibold leading-snug text-ink-gray-9 [overflow-wrap:anywhere]"
					>
						{{ talk.title }}
					</div>
					<div class="truncate text-p-xs text-ink-gray-5">{{ speakerLine(talk.speakers) }}</div>
					<div class="mt-1 flex flex-wrap items-center gap-1">
						<Badge
							size="sm"
							:label="talkType?.title ?? 'Talk'"
							:theme="badgeTheme(talkType?.color)"
						/>
						<Badge size="sm" :label="`${duration} min`" theme="gray" />
						<Badge size="sm" label="Accepted" theme="green" variant="outline" />
					</div>
				</div>
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-plus"
					label="Add to next free slot"
					@click="add(talk.name)"
				/>
			</div>

			<div
				v-if="!builder.talks.value.length"
				class="flex flex-col items-start gap-2.5 rounded-6 border border-dashed border-outline-gray-3 p-4"
			>
				<span class="lucide-inbox size-[18px] text-ink-gray-6" aria-hidden="true" />
				<div>
					<div class="text-p-sm font-semibold text-ink-gray-9">No talks yet</div>
					<div class="mt-0.5 text-p-xs leading-snug text-ink-gray-5">
						Accepted proposals show up here. You can still add breaks and custom items.
					</div>
				</div>
				<div class="flex flex-wrap gap-1.5">
					<Button
						variant="subtle"
						size="sm"
						iconLeft="lucide-arrow-up-right"
						label="Open proposals"
						:route="{ name: 'event-talks' }"
					/>
					<Button
						variant="ghost"
						size="sm"
						label="Add custom item"
						@click="board.tab.value = 'custom'"
					/>
				</div>
			</div>
			<div
				v-else-if="!matching.length"
				class="flex flex-col items-center gap-2 px-2 py-5 text-center"
			>
				<div class="text-p-sm text-ink-gray-7 [overflow-wrap:anywhere]">
					No talks match “{{ search.trim() }}”
				</div>
				<Button variant="subtle" size="sm" label="Clear search" @click="search = ''" />
			</div>
			<div
				v-else-if="!unscheduled.length"
				class="rounded-5 border border-dashed border-outline-gray-2 px-2 py-3.5 text-center text-p-xs text-ink-gray-5"
			>
				Every matching talk is on the schedule
			</div>
		</div>
		<p
			class="shrink-0 border-t border-outline-gray-1 px-3.5 py-2.5 text-p-xs leading-snug text-ink-gray-5"
		>
			Drag a talk onto the schedule. Drop a block back here to unschedule it.
		</p>
	</div>
</template>
