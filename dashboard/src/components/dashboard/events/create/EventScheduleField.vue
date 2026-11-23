<script setup lang="ts">
import { ErrorMessage } from "frappe-ui"
import { computed } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"
import { isEndBeforeStart } from "@/utils/eventDates"

import ScheduleInlineRows from "./schedule/ScheduleInlineRows.vue"
import ScheduleRangePicker from "./schedule/ScheduleRangePicker.vue"
import type { ScheduleDraft } from "./schedule/scheduleTime"
import TimeZoneButton from "./schedule/TimeZoneButton.vue"

// Date range three fifths, zone two fifths. A phone stacks them and edits the range in
// rows on the page, since a popover that size does not fit its screen.
const props = defineProps<{ schedule: ScheduleDraft; disabled?: boolean }>()
const isMobile = useIsMobile()

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
			<ScheduleInlineRows v-if="isMobile" :schedule="schedule" :disabled="disabled" />
			<ScheduleRangePicker v-else :schedule="schedule" :disabled="disabled" class="min-w-0" />
			<TimeZoneButton v-model="schedule.timeZone" :disabled="disabled" />
		</div>
		<ErrorMessage v-if="backwards" :message="__('The event must end after it starts')" />
	</div>
</template>
