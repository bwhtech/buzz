<script setup lang="ts">
import { ErrorMessage } from "frappe-ui"
import { computed } from "vue"

import { isEndBeforeStart } from "@/utils/eventDates"

import ScheduleRangePicker from "./ScheduleRangePicker.vue"
import type { ScheduleDraft } from "./scheduleTime"
import TimeZoneButton from "./TimeZoneButton.vue"

// Date range three fifths, zone two fifths; a phone stacks them.
const props = defineProps<{ schedule: ScheduleDraft; disabled?: boolean }>()

const backwards = computed(() =>
	isEndBeforeStart(
		props.schedule.startDate,
		props.schedule.endDate,
		props.schedule.startTime,
		props.schedule.endTime,
	),
)
</script>

<template>
	<div class="flex flex-col gap-2">
		<div class="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
			<ScheduleRangePicker :schedule="schedule" :disabled="disabled" class="min-w-0" />
			<TimeZoneButton v-model="schedule.timeZone" :disabled="disabled" />
		</div>
		<ErrorMessage v-if="backwards" :message="__('The event must end after it starts')" />
	</div>
</template>
