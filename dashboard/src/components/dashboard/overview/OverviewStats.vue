<script setup lang="ts">
import { AreaChart, DonutChart } from "frappe-ui/charts"
import { computed } from "vue"

import MetricCard from "./MetricCard.vue"
import type { Metric } from "./overviewMetrics"

// Registrations over time lead, with their split by ticket beside them; any other metric
// with numbers sits underneath as a card. Nothing yet: one line says why.
const props = defineProps<{ metrics: Metric[] }>()

const lead = computed(() => props.metrics.find((metric) => metric.key === "registrations"))
const rest = computed(() => props.metrics.filter((metric) => metric !== lead.value))
const restColumns = computed(() => (rest.value.length > 1 ? "sm:grid-cols-2" : ""))
</script>

<template>
	<section class="space-y-3">
		<h2 class="flex h-7 items-center text-lg font-semibold text-ink-gray-9">At a glance</h2>

		<p v-if="!metrics.length" class="text-p-base text-ink-gray-5">
			Numbers show up here after the first registration. Share the link to get it.
		</p>

		<div v-if="lead" class="grid gap-3 sm:grid-cols-3">
			<div class="rounded-5 border border-outline-gray-2 bg-surface-elevation-1 p-4 sm:col-span-2">
				<div class="h-56">
					<AreaChart
						:title="lead.label"
						:subtitle="`${lead.total} registered`"
						:data="lead.perDay"
						x="date"
						y="value"
						:x-axis="{ type: 'time', timeGrain: 'day' }"
						:y-axis="{ integer: true }"
						:series-config="{ value: { label: lead.label, color: lead.color } }"
						smooth
					/>
				</div>
			</div>
			<div class="split-donut rounded-5 border border-outline-gray-2 bg-surface-elevation-1 p-4">
				<div class="h-56">
					<DonutChart
						title="By ticket"
						:data="lead.breakdown"
						category="label"
						value="count"
						center-label="guests"
					/>
				</div>
			</div>
		</div>

		<div v-if="rest.length" class="grid gap-3" :class="restColumns">
			<MetricCard v-for="metric in rest" :key="metric.key" :metric="metric" />
		</div>
	</section>
</template>

<style scoped>
/* The donut's legend wraps taller than the ring; the tooltip already names each slice. */
.split-donut :deep([data-slot="chart-legend"]) {
	display: none;
}
</style>
