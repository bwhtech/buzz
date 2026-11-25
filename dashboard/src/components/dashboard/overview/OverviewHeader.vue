<script setup lang="ts">
import { Avatar, Breadcrumbs, Button, PageHeader } from "frappe-ui"
import { computed } from "vue"

import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import { useIsMobile } from "@/composables/useIsMobile"

import type { EventSummary } from "./overviewData"

// On desktop the crumbs stay hidden while the big "Overview" heading is on screen, and
// slide in once it scrolls away. Mobile keeps the shared event header.
const props = defineProps<{ summary: EventSummary; headingVisible: boolean }>()

const isMobile = useIsMobile()
const crumbs = computed(() => [{ label: props.summary.title || "Event" }, { label: "Overview" }])
const eventPage = computed(() => (props.summary.route ? `/${props.summary.route}` : undefined))
const teamRoute = computed(() =>
	props.summary.teamId
		? { name: "team-calendar", params: { teamId: props.summary.teamId } }
		: undefined,
)
</script>

<template>
	<EventPageHeader v-if="isMobile" :title="summary.title" section="Overview" />
	<PageHeader v-else class="border-none bg-surface-elevation-1 pt-2">
		<div
			class="overview-crumb min-w-0"
			:data-shown="!headingVisible || undefined"
			:aria-hidden="headingVisible"
		>
			<Breadcrumbs :items="crumbs" />
		</div>
		<div class="flex shrink-0 items-center gap-1">
			<Button v-if="summary.teamName" variant="ghost" class="!pl-1.5" :route="teamRoute">
				<template #prefix>
					<Avatar :image="summary.teamLogo" :label="summary.teamName" size="xs" shape="square" />
				</template>
				<span class="text-ink-gray-7">{{ summary.teamName }}</span>
			</Button>
			<Button
				variant="ghost"
				:link="eventPage"
				icon-right="lucide-arrow-up-right"
				label="Event Page"
			/>
		</div>
	</PageHeader>
</template>

<style scoped>
/* Entering is slower than leaving: the eye is looking for it on the way in. */
.overview-crumb {
	transition:
		opacity 160ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.overview-crumb[data-shown] {
	transition-duration: 240ms;
}
.overview-crumb:not([data-shown]) {
	opacity: 0;
	transform: translateY(8px);
	pointer-events: none;
}
@media (prefers-reduced-motion: reduce) {
	.overview-crumb {
		transform: none !important;
	}
}
</style>
