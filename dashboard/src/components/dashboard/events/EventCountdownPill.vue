<script setup lang="ts">
import { useNow } from "@vueuse/core"
import { Badge, dayjs } from "frappe-ui"
import { computed } from "vue"

import type { MyEvent } from "@/types"

const props = defineProps<{ event: MyEvent }>()

const now = useNow({ interval: 60_000 })

function moment(date: string, time: string | null) {
	return dayjs(`${date} ${time || "00:00:00"}`)
}

const startsOn = computed(() => moment(props.event.start_date, props.event.start_time))

// An event with no closing time runs to the end of its last day.
const endsOn = computed(() => {
	const { start_date, end_date, end_time } = props.event
	const lastDay = end_date || start_date
	return end_time ? moment(lastDay, end_time) : moment(lastDay, null).endOf("day")
})

const minutesToStart = computed(() => startsOn.value.diff(now.value, "minute"))

const isLive = computed(() => minutesToStart.value <= 0 && dayjs(now.value).isBefore(endsOn.value))

// Time left on the viewer's own clock: "14d 5h 55m", with the leading empty units dropped.
const countdown = computed(() => {
	const minutes = minutesToStart.value
	if (minutes <= 0) return null
	const days = Math.floor(minutes / 1440)
	const hours = Math.floor((minutes % 1440) / 60)
	const parts = [`${minutes % 60}m`]
	if (days || hours) parts.unshift(`${hours}h`)
	if (days) parts.unshift(`${days}d`)
	return parts.join(" ")
})
</script>

<template>
	<Badge v-if="isLive || countdown" class="font-medium shadow">
		<template v-if="isLive" #prefix>
			<span class="relative flex size-2">
				<span
					class="absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-75 motion-safe:animate-ping"
				/>
				<span class="relative inline-flex size-2 rounded-full bg-green-600" />
			</span>
		</template>

		<span v-if="isLive" class="text-xs text-inherit">Live</span>
		<template v-else>
			<span class="text-xs text-inherit">Starting in</span>
			<span class="text-xs font-semibold tabular-nums text-ink-gray-8">{{ countdown }}</span>
		</template>
	</Badge>
</template>
