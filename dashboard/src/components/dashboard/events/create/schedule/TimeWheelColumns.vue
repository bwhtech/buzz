<script setup lang="ts">
import { computed } from "vue"

import { minutesOf, timeOf } from "./scheduleTime"
import WheelColumn from "./WheelColumn.vue"

// Hour, minute and AM/PM wheels under one centre band, in five-minute steps.
const time = defineModel<string>({ required: true })

const pad = (value: number) => String(value).padStart(2, "0")
const HOURS = Array.from({ length: 12 }, (_, index) => ({
	value: String(index + 1),
	label: String(index + 1),
}))
const MINUTES = Array.from({ length: 12 }, (_, index) => ({
	value: String(index * 5),
	label: pad(index * 5),
}))
const MERIDIEMS = [
	{ value: "AM", label: "AM" },
	{ value: "PM", label: "PM" },
]

const parts = computed(() => {
	const total = minutesOf(time.value)
	const hour = Math.floor(total / 60)
	return {
		hour: String(hour % 12 || 12),
		minute: String((Math.round((total % 60) / 5) * 5) % 60),
		meridiem: hour < 12 ? "AM" : "PM",
	}
})

function update(patch: Partial<typeof parts.value>) {
	const next = { ...parts.value, ...patch }
	const hourOfDay = (Number(next.hour) % 12) + (next.meridiem === "PM" ? 12 : 0)
	time.value = timeOf(hourOfDay * 60 + Number(next.minute))
}

const hour = computed({
	get: () => parts.value.hour,
	set: (value: string) => update({ hour: value }),
})
const minute = computed({
	get: () => parts.value.minute,
	set: (value: string) => update({ minute: value }),
})
const meridiem = computed({
	get: () => parts.value.meridiem,
	set: (value: string) => update({ meridiem: value }),
})
</script>

<template>
	<div class="relative grid grid-cols-3 px-6">
		<span
			class="pointer-events-none absolute inset-x-3 top-1/2 h-[34px] -translate-y-1/2 rounded-4 bg-surface-gray-2"
			aria-hidden="true"
		/>
		<WheelColumn v-model="hour" :items="HOURS" :label="__('Hour')" class="relative" />
		<WheelColumn v-model="minute" :items="MINUTES" :label="__('Minute')" class="relative" />
		<WheelColumn v-model="meridiem" :items="MERIDIEMS" :label="__('AM or PM')" class="relative" />
	</div>
</template>
