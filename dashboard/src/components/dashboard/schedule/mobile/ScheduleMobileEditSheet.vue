<script setup lang="ts">
import { Badge, BottomSheet, Button, TabButtons } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { badgeStyle } from "../scheduleColors"
import { DAY_END, MIN_DURATION, clamp, clock, durationLabel } from "../scheduleLayout"
import type { ScheduleItem } from "../scheduleTypes"
import { useBuilder } from "../useScheduleBoard"
import ScheduleMobileChip from "./ScheduleMobileChip.vue"
import { useMobile } from "./useScheduleMobile"

const DURATIONS = [5, 10, 15, 20, 30, 45, 60, 90, 120]
const SHIFT_MINUTES = 5
const builder = useBuilder()
const mobile = useMobile()

// The last edited key outlives the sheet, so its content stays put while it slides out.
const key = ref<string | null>(null)
watch(mobile.sheet, (sheet) => sheet?.type === "edit" && (key.value = sheet.key), {
	immediate: true,
})
const open = computed(() => mobile.sheet.value?.type === "edit")
const item = computed(() => (key.value ? builder.findItem(key.value) : undefined))
const details = computed(() => (item.value ? builder.itemDetails(item.value) : null))
const isTalk = computed(() => !!item.value?.talk)
const conflict = computed(() => (item.value ? builder.conflictOf(item.value) : ""))
const range = computed(() => builder.rangeOf(item.value?.date ?? ""))

const dayOptions = builder.dayOptions
const trackOptions = computed(() => [
	...(isTalk.value ? [] : [{ name: null, title: "All tracks" }]),
	...builder.tracks.tracks.value,
])

function change(patch: Partial<ScheduleItem>) {
	if (item.value) builder.update(item.value.key, patch)
}

function shiftStart(minutes: number) {
	if (!item.value) return
	const latest = range.value.end - item.value.duration
	change({ start: clamp(item.value.start + minutes, range.value.start, latest) })
}

function shiftEnd(minutes: number) {
	if (!item.value) return
	const longest = DAY_END - item.value.start
	change({ duration: clamp(item.value.duration + minutes, MIN_DURATION, longest) })
}

function setDay(date: string | number) {
	if (!item.value) return
	builder.place({ kind: "item", id: item.value.key }, String(date))
	builder.activeDate.value = String(date)
}

function remove() {
	if (item.value) builder.remove(item.value.key)
	mobile.closeSheet()
}
</script>

<template>
	<BottomSheet :open="open" @update:open="(value) => !value && mobile.closeSheet()">
		<div v-if="item && details" class="flex flex-col">
			<div class="px-5 pt-2">
				<div class="mb-2.5 flex items-center gap-1.5">
					<Badge
						:style="badgeStyle(details.type?.color)"
						:label="details.type?.title ?? item.type"
					/>
					<Badge v-if="conflict" theme="red" :label="conflict" />
				</div>
				<div
					v-if="isTalk"
					class="text-xl font-semibold leading-snug text-ink-gray-9 [overflow-wrap:anywhere]"
				>
					{{ details.title }}
				</div>
				<input
					v-else
					:value="item.title"
					placeholder="Untitled item"
					aria-label="Title"
					class="w-full bg-transparent text-xl font-semibold leading-snug text-ink-gray-9 outline-none placeholder:text-ink-gray-4"
					@input="builder.retitle(item.key, ($event.target as HTMLInputElement).value)"
					@change="builder.recordChange"
				/>
				<div
					v-if="details.speakers.length"
					class="mt-1 text-p-base text-ink-gray-5 [overflow-wrap:anywhere]"
				>
					{{ details.speakers.join(", ") }}
				</div>

				<div class="mt-4 flex flex-col border-t border-outline-gray-1">
					<div class="flex items-center gap-3 border-b border-outline-gray-1 py-3">
						<div class="w-[72px] shrink-0 text-p-sm text-ink-gray-5">Day</div>
						<div
							class="[scrollbar-width:none] [&::-webkit-scrollbar]:hidden min-w-0 flex-1 overflow-x-auto"
						>
							<TabButtons
								:model-value="item.date"
								:options="dayOptions"
								@update:model-value="setDay"
							/>
						</div>
					</div>
					<div class="flex items-center gap-3 border-b border-outline-gray-1 py-3">
						<div class="w-[72px] shrink-0 text-p-sm text-ink-gray-5">Starts</div>
						<div class="flex flex-1 items-center gap-2">
							<Button
								variant="outline"
								icon="lucide-minus"
								label="5 minutes earlier"
								@click="shiftStart(-SHIFT_MINUTES)"
							/>
							<div class="flex-1 text-center text-base font-semibold tabular-nums text-ink-gray-9">
								{{ clock(item.start) }}
							</div>
							<Button
								variant="outline"
								icon="lucide-plus"
								label="5 minutes later"
								@click="shiftStart(SHIFT_MINUTES)"
							/>
						</div>
					</div>
					<div class="flex items-center gap-3 border-b border-outline-gray-1 py-3">
						<div class="w-[72px] shrink-0 text-p-sm text-ink-gray-5">Ends</div>
						<div class="flex flex-1 items-center gap-2">
							<Button
								variant="outline"
								icon="lucide-minus"
								label="End 5 minutes earlier"
								@click="shiftEnd(-SHIFT_MINUTES)"
							/>
							<div class="flex-1 text-center text-base font-semibold tabular-nums text-ink-gray-9">
								{{ clock(item.start + item.duration) }}
							</div>
							<Button
								variant="outline"
								icon="lucide-plus"
								label="End 5 minutes later"
								@click="shiftEnd(SHIFT_MINUTES)"
							/>
						</div>
					</div>
					<div class="flex items-start gap-3 border-b border-outline-gray-1 py-3">
						<div class="w-[72px] shrink-0 pt-1.5 text-p-sm text-ink-gray-5">Length</div>
						<div
							class="[scrollbar-width:none] [&::-webkit-scrollbar]:hidden flex min-w-0 flex-1 gap-1.5 overflow-x-auto"
						>
							<ScheduleMobileChip
								v-for="minutes in DURATIONS"
								:key="minutes"
								size="lg"
								class="tabular-nums"
								:active="minutes === item.duration"
								@click="change({ duration: minutes })"
							>
								{{ durationLabel(minutes) }}
							</ScheduleMobileChip>
						</div>
					</div>
					<div class="flex items-start gap-3 py-3">
						<div class="w-[72px] shrink-0 pt-1.5 text-p-sm text-ink-gray-5">Track</div>
						<div class="flex min-w-0 flex-1 flex-wrap gap-1.5">
							<ScheduleMobileChip
								v-for="track in trackOptions"
								:key="track.name ?? 'all'"
								size="lg"
								:active="track.name === item.track"
								@click="change({ track: track.name })"
							>
								{{ track.title }}
							</ScheduleMobileChip>
						</div>
					</div>
				</div>
			</div>
			<div class="flex gap-2 px-5 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-3.5">
				<Button
					class="flex-1"
					variant="subtle"
					theme="red"
					size="lg"
					iconLeft="lucide-calendar-x"
					:label="isTalk ? 'Unschedule' : 'Delete'"
					@click="remove"
				/>
				<Button class="flex-1" variant="solid" size="lg" label="Done" @click="mobile.closeSheet" />
			</div>
		</div>
	</BottomSheet>
</template>
