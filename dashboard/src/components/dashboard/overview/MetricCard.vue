<script setup lang="ts">
import { NumberCard } from "frappe-ui/charts"
import { computed } from "vue"

import type { Metric } from "./overviewMetrics"

const props = defineProps<{ metric: Metric }>()

const sparkline = computed(() =>
	props.metric.perDay.length
		? {
				data: props.metric.perDay.map((day) => day.value),
				type: "area" as const,
				color: props.metric.color,
			}
		: undefined,
)
</script>

<template>
	<div class="rounded-5 border border-outline-gray-2 bg-surface-elevation-1 p-4">
		<NumberCard
			:card="false"
			:title="metric.label"
			:value="metric.total"
			:prefix="metric.prefix"
			:delta="metric.delta"
			delta-caption="vs yesterday"
			:sparkline="sparkline"
		/>
	</div>
</template>
