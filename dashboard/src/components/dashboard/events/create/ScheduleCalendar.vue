<script setup lang="ts">
import { Button, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import { today } from "./scheduleTime"

// One month, Monday first, with the picked range banded between its two ends.
const props = defineProps<{ start?: string; end?: string; min?: string }>()
const emit = defineEmits<{ pick: [date: string]; hover: [date: string] }>()
const month = defineModel<string>("month", { required: true })

const WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
const todayDate = today()

const first = computed(() => dayjsLocal(month.value).startOf("month"))
const shift = (by: number) => (month.value = first.value.add(by, "month").format("YYYY-MM-DD"))

// Padded with blanks so the 1st lands under its weekday.
const cells = computed(() => {
	const lead = (first.value.day() + 6) % 7
	const days = Array.from({ length: first.value.daysInMonth() }, (_, index) =>
		first.value.add(index, "day").format("YYYY-MM-DD"),
	)
	return [...Array<string>(lead).fill(""), ...days]
})

const isRange = computed(() => Boolean(props.start && props.end && props.end > props.start))

function band(date: string) {
	if (!isRange.value || !props.start || !props.end) return ""
	if (date === props.start) return "start"
	if (date === props.end) return "end"
	return date > props.start && date < props.end ? "middle" : ""
}

const isEndpoint = (date: string) => date === props.start || date === props.end
const isDisabled = (date: string) => Boolean(props.min && date < props.min)
</script>

<template>
	<div class="w-full select-none">
		<div class="flex h-7 items-center justify-between">
			<span class="text-sm font-medium text-ink-gray-9">{{ first.format("MMMM YYYY") }}</span>
			<div class="-mr-1 flex">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-chevron-left"
					aria-label="Previous month"
					@click="shift(-1)"
				/>
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-chevron-right"
					aria-label="Next month"
					@click="shift(1)"
				/>
			</div>
		</div>
		<div class="mt-1.5 grid grid-cols-7 text-center text-xs text-ink-gray-5">
			<span
				v-for="weekday in WEEKDAYS"
				:key="weekday"
				class="flex h-7 items-center justify-center"
				>{{ weekday }}</span
			>
		</div>
		<div class="grid grid-cols-7" @mouseleave="emit('hover', '')">
			<template v-for="(date, index) in cells" :key="date || `blank-${index}`">
				<span v-if="!date" />
				<button
					v-else
					type="button"
					class="day relative flex h-9 items-center justify-center text-sm tabular-nums"
					:disabled="isDisabled(date)"
					:aria-pressed="isEndpoint(date)"
					:aria-label="dayjsLocal(date).format('dddd, D MMMM YYYY')"
					@click="emit('pick', date)"
					@mouseenter="emit('hover', date)"
				>
					<span
						v-if="band(date)"
						class="absolute inset-y-0 bg-surface-gray-2"
						:class="{
							'left-1/2 right-0': band(date) === 'start',
							'left-0 right-1/2': band(date) === 'end',
							'inset-x-0': band(date) === 'middle',
						}"
						aria-hidden="true"
					/>
					<span
						class="day-face relative flex size-9 items-center justify-center rounded-full"
						:class="
							isEndpoint(date)
								? 'day-selected font-semibold'
								: isDisabled(date)
									? 'text-ink-gray-3 line-through'
									: 'text-ink-gray-8'
						"
					>
						{{ dayjsLocal(date).date() }}
						<span
							v-if="date === todayDate && !isEndpoint(date)"
							class="absolute bottom-1.5 size-1 rounded-full bg-ink-gray-9"
							aria-hidden="true"
						/>
					</span>
				</button>
			</template>
		</div>
	</div>
</template>

<style scoped>
@media (hover: hover) and (pointer: fine) {
	.day:not(:disabled):not([aria-pressed="true"]):hover .day-face {
		box-shadow: inset 0 0 0 1px var(--outline-gray-4, #9ca3af);
	}
}
/* Inverted ink pair, so the picked day reads in both themes. */
.day-selected {
	background: var(--surface-gray-10, var(--ink-gray-9));
	color: var(--ink-base);
}
.day-face {
	transition:
		transform 140ms cubic-bezier(0.23, 1, 0.32, 1),
		background-color 150ms ease;
}
.day:not(:disabled):active .day-face {
	transform: scale(0.94);
}
.day:disabled {
	cursor: default;
}
</style>
