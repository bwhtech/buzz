<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"

import { clock } from "../scheduleLayout"
import { useDayLayout } from "../useDayLayout"
import { buildAgenda } from "./scheduleMobileAgenda"
import ScheduleMobileCard from "./ScheduleMobileCard.vue"
import { ALL_ROOMS, useMobile } from "./useScheduleMobile"

const { builder, board, dayItems, roomIndex, conflicts } = useDayLayout()
const mobile = useMobile()

const filter = mobile.roomFilter
const visibleItems = computed(() =>
	dayItems.value.filter(
		(item) => filter.value === ALL_ROOMS || !item.room || item.room === filter.value,
	),
)
const gapRoom = computed(() => (filter.value === ALL_ROOMS ? null : filter.value))
const entries = computed(() =>
	buildAgenda(visibleItems.value, roomIndex.value, board.range.value.end),
)
const dayLabel = computed(() => builder.activeDay.value?.label)
</script>

<template>
	<div class="min-h-0 flex-1 overflow-y-auto px-4 pb-36 pt-2">
		<template v-for="entry in entries" :key="`${entry.kind}-${entry.start}`">
			<button
				v-if="entry.kind === 'gap'"
				type="button"
				class="my-1.5 ml-[54px] flex w-[calc(100%-54px)] items-center justify-between gap-2 rounded-5 border border-dashed border-outline-gray-2 px-3 py-2 text-left text-p-xs text-ink-gray-5 transition-transform duration-100 active:scale-[0.98]"
				@click="mobile.openAdd(entry.start, gapRoom)"
			>
				<span>{{ entry.label }}</span>
				<span class="flex items-center gap-1 font-medium text-ink-gray-7">
					<span class="lucide-plus size-3.5" aria-hidden="true" />Add
				</span>
			</button>
			<div v-else class="flex gap-3 py-1.5">
				<div class="w-[42px] shrink-0 pt-2.5 text-p-sm font-semibold tabular-nums text-ink-gray-9">
					{{ clock(entry.start) }}
				</div>
				<div class="flex min-w-0 flex-1 flex-col gap-1.5">
					<ScheduleMobileCard
						v-for="item in entry.items"
						:key="item.key"
						:item="item"
						:conflict="conflicts[item.key]"
						@click="mobile.openEdit(item.key)"
					/>
				</div>
			</div>
		</template>
		<div v-if="!entries.length" class="flex flex-col items-center gap-1.5 px-6 pt-16 text-center">
			<div
				class="mb-2.5 grid size-12 place-items-center rounded-5 bg-surface-gray-2 text-ink-gray-6"
			>
				<span class="lucide-calendar-plus size-[22px]" aria-hidden="true" />
			</div>
			<div class="text-lg font-semibold text-ink-gray-9">Nothing scheduled on {{ dayLabel }}</div>
			<div class="mb-3.5 max-w-[260px] text-p-base text-ink-gray-5">
				{{
					mobile.unscheduledTalks.value.length
						? `${mobile.unscheduledTalks.value.length} accepted talks are ready to place`
						: "Add breaks, lunch and other items as talks get accepted"
				}}
			</div>
			<Button
				variant="solid"
				iconLeft="lucide-plus"
				label="Add session"
				@click="mobile.openAdd()"
			/>
		</div>
	</div>
</template>
