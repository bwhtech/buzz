<script setup lang="ts">
import { BottomSheet, Button, TabButtons, TextInput, dayjs } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { blockColors, dotColor } from "../scheduleColors"
import { scheduleIcon } from "../scheduleIcons"
import { clamp, clock, durationLabel, speakerLine, talkMatches } from "../scheduleLayout"
import { useBuilder } from "../useScheduleBoard"
import ScheduleMobileChip from "./ScheduleMobileChip.vue"
import { type MobileSheet, useMobile } from "./useScheduleMobile"

type AddSheet = Extract<MobileSheet, { type: "add" }>

const STEP_MINUTES = 15
const builder = useBuilder()
const mobile = useMobile()
const tab = ref<"talks" | "custom">("talks")
const search = ref("")

// The last add sheet outlives the sheet, so its content stays put while it slides out.
const lastAddSheet = ref<AddSheet | null>(null)
watch(
	mobile.sheet,
	(sheet) => {
		if (sheet?.type !== "add") return
		lastAddSheet.value = sheet
		search.value = ""
	},
	{ immediate: true },
)
const open = computed(() => mobile.sheet.value?.type === "add")
const add = computed(() => lastAddSheet.value)

const range = computed(() => builder.rangeOf(builder.activeDate.value))
const sheetSubtitle = computed(
	() =>
		`${builder.activeDay.value?.label} · ${dayjs(builder.activeDate.value).format("ddd D MMM")}`,
)
const talkDuration = builder.talkDuration
const tabOptions = computed(() => [
	{ label: `Talks ${mobile.unscheduledTalks.value.length}`, value: "talks" },
	{ label: "Breaks & custom", value: "custom" },
])
const talks = computed(() => {
	const query = search.value.trim().toLowerCase()
	return mobile.unscheduledTalks.value.filter((talk) => talkMatches(talk, query))
})
const customTypes = builder.itemTypes
const noTalksText = computed(() => {
	if (!builder.tracks.tracks.value.length) return "Add a track to place talks"
	if (!builder.talks.value.length) return "No accepted talks yet"
	if (!mobile.unscheduledTalks.value.length) return "Every talk is on the schedule"
	return `No talks match “${search.value.trim()}”`
})

function update(patch: Partial<AddSheet>) {
	if (add.value) mobile.sheet.value = { ...add.value, ...patch }
}

function stepStart(step: number) {
	if (!add.value) return
	const start = add.value.start + step
	update({ start: clamp(start, range.value.start, range.value.end - STEP_MINUTES) })
}

function place(kind: "talk" | "type", id: string) {
	if (!add.value) return
	const placed = builder.place(
		{ kind, id },
		builder.activeDate.value,
		add.value.track,
		add.value.start,
	)
	mobile.closeSheet()
	if (placed?.type === "Custom") mobile.openEdit(placed.key)
}
</script>

<template>
	<BottomSheet :open="open" @update:open="(value) => !value && mobile.closeSheet()">
		<div v-if="add" class="flex flex-col">
			<div class="flex flex-col gap-3 px-5 pb-3 pt-2">
				<div class="flex items-center gap-2">
					<div class="min-w-0 flex-1">
						<div class="text-lg font-semibold text-ink-gray-9">Add session</div>
						<div class="truncate text-p-sm text-ink-gray-5">{{ sheetSubtitle }}</div>
					</div>
					<Button
						variant="outline"
						size="sm"
						icon="lucide-minus"
						label="Earlier"
						@click="stepStart(-STEP_MINUTES)"
					/>
					<div class="w-11 text-center text-p-base font-semibold tabular-nums text-ink-gray-9">
						{{ clock(add.start) }}
					</div>
					<Button
						variant="outline"
						size="sm"
						icon="lucide-plus"
						label="Later"
						@click="stepStart(STEP_MINUTES)"
					/>
				</div>
				<div
					class="flex gap-1.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
				>
					<ScheduleMobileChip
						v-for="track in builder.tracks.tracks.value"
						:key="track.name"
						:active="track.name === add.track"
						@click="update({ track: track.name })"
					>
						{{ track.title }}
					</ScheduleMobileChip>
				</div>
				<TabButtons fluid v-model="tab" :options="tabOptions" />
				<TextInput
					v-if="tab === 'talks'"
					v-model="search"
					placeholder="Search talks or speakers"
					autocomplete="off"
				>
					<template #prefix
						><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
					/></template>
				</TextInput>
			</div>
			<div class="min-h-[280px] px-3 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
				<template v-if="tab === 'talks'">
					<button
						v-for="talk in talks"
						:key="talk.name"
						type="button"
						class="flex w-full items-center gap-3 rounded-5 px-2 py-2.5 text-left transition-transform duration-100 hover:bg-surface-gray-2 active:scale-[0.98]"
						@click="place('talk', talk.name)"
					>
						<span
							class="size-[7px] shrink-0 rounded-full"
							:style="{ background: dotColor(builder.typesByName.value.Talk?.color) }"
						/>
						<span class="min-w-0 flex-1">
							<span class="block truncate text-p-base font-medium text-ink-gray-9">{{
								talk.title
							}}</span>
							<span class="block truncate text-p-xs text-ink-gray-5">
								{{ speakerLine(talk.speakers) }} · {{ durationLabel(talkDuration) }}
							</span>
						</span>
					</button>
					<div
						v-if="!talks.length || !builder.tracks.tracks.value.length"
						class="px-4 py-9 text-center text-p-base text-ink-gray-5"
					>
						{{ noTalksText }}
					</div>
				</template>
				<div v-else class="grid grid-cols-2 gap-2 px-2">
					<button
						v-for="type in customTypes"
						:key="type.name"
						type="button"
						class="flex flex-col items-start gap-2.5 rounded-5 border border-outline-gray-2 bg-surface-base p-3.5 text-left transition-transform duration-100 active:scale-[0.97]"
						@click="place('type', type.name)"
					>
						<span
							class="grid size-8 place-items-center rounded-4"
							:style="{
								background: blockColors(type.color).background,
								color: blockColors(type.color).meta,
							}"
						>
							<span
								:class="[scheduleIcon(type.icon) || 'lucide-calendar-clock', 'size-4']"
								aria-hidden="true"
							/>
						</span>
						<span>
							<span class="block text-p-base font-medium text-ink-gray-9">{{
								type.name === "Custom" ? "Untitled item" : type.title
							}}</span>
							<span class="block text-p-xs text-ink-gray-5">
								{{ durationLabel(type.default_duration) }} ·
								{{ type.spans_all_tracks ? "All tracks" : "One track" }}
							</span>
						</span>
					</button>
				</div>
			</div>
		</div>
	</BottomSheet>
</template>
