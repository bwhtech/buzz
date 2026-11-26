<script setup lang="ts">
import { useElementVisibility } from "@vueuse/core"
import { ref } from "vue"
import { useRoute } from "vue-router"

import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import { useEventOverview } from "@/components/dashboard/overview/overviewData"
import OverviewHero from "@/components/dashboard/overview/OverviewHero.vue"
import OverviewStats from "@/components/dashboard/overview/OverviewStats.vue"
import SetupSteps from "@/components/dashboard/overview/SetupSteps.vue"

const eventId = useRoute().params.eventId as string
const { summary, steps, metrics, metricsLoaded } = useEventOverview(eventId)

// The heading counts as gone once it scrolls out of the page body.
const heading = ref<HTMLElement>()
const headingVisible = useElementVisibility(heading, { initialValue: true })
</script>

<template>
	<div class="min-h-full bg-surface-elevation-1">
		<EventPageHeader :title="summary.title" section="Overview" :hide-crumbs="headingVisible" />

		<main class="overview-page mx-auto flex max-w-[800px] flex-col gap-10 px-4 pb-40 pt-4">
			<EventArchivedAlert :event="eventId" />
			<h1
				ref="heading"
				class="-mb-3 text-4xl font-semibold tracking-[-0.02em] text-ink-gray-9 max-sm:hidden"
			>
				Overview
			</h1>

			<OverviewHero
				v-if="summary.title"
				class="overview-section"
				:summary="summary"
				:event-id="eventId"
			/>
			<SetupSteps v-if="steps.length" class="overview-section" :steps="steps" :summary="summary" />
			<OverviewStats v-if="metricsLoaded" class="overview-section" :metrics="metrics" />
		</main>
	</div>
</template>

<style scoped>
/* Sections fade in as their data arrives, then stay put. */
.overview-section {
	animation: section-fade 240ms ease-out both;
}
@keyframes section-fade {
	from {
		opacity: 0;
	}
}
</style>
