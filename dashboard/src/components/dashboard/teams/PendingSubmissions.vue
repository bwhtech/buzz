<script setup lang="ts">
import { Badge, useCall } from "frappe-ui"
import { computed, ref, watch } from "vue"

import EventDrawer from "@/components/dashboard/events/EventDrawer.vue"
import PendingSubmission from "@/components/dashboard/teams/PendingSubmission.vue"
import { useDrawerSelection } from "@/composables/useDrawerSelection"
import { useRevealOnScroll } from "@/composables/useRevealOnScroll"
import type { CommunityQueue, CommunityRequest, MyEvent } from "@/types"

const props = defineProps<{ community: string; canReview: boolean }>()
const emit = defineEmits<{ changed: [] }>()

// Not immediate: the server refuses the queue to anyone who cannot review it.
const queue = useCall<CommunityQueue, { community: string }>({
	url: "/api/v2/method/buzz.api.communities.get_requests",
	params: () => ({ community: props.community }),
	immediate: false,
})
watch(
	() => props.canReview,
	(canReview) => canReview && queue.fetch(),
	{ immediate: true },
)

const pending = computed(() => queue.data?.pending ?? [])

// A long queue scrolls in its own box, so the calendar below stays a scroll away.
const list = ref<HTMLElement | null>(null)
const { visible, sentinel } = useRevealOnScroll(() => pending.value, 10, list)

const drawer = useDrawerSelection<MyEvent>()

// A Buzz event opens in the drawer; an external one, on the platform it lives on.
function open(request: CommunityRequest) {
	if (request.is_external_event) return window.open(request.event_url || "", "_blank", "noopener")
	drawer.show({
		name: request.event || request.name,
		title: request.event_title,
		route: request.event_route,
		start_date: request.start_date,
		end_date: null,
		start_time: request.start_time,
		end_time: null,
		venue: request.place,
		medium: null,
		banner_image: request.banner_image,
		allow_editing_talks_after_acceptance: false,
		is_host: false,
		is_attendee: false,
		team: request.event_team,
		team_name: request.event_team_name,
		team_logo: request.event_team_logo,
	})
}

function reviewed() {
	queue.reload()
	emit("changed")
}
</script>

<template>
	<section v-if="pending.length" class="space-y-3 border-b border-outline-gray-2 pb-8">
		<div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
			<h2 class="flex items-center gap-2 text-xl font-semibold text-ink-gray-9">
				{{ __("Pending Approval") }}
				<Badge :label="String(pending.length)" size="md" />
			</h2>
			<p class="text-sm text-ink-gray-5">{{ __("Not on your calendar until approved") }}</p>
		</div>
		<div
			ref="list"
			class="max-h-[22rem] overflow-y-auto overscroll-contain rounded-8 border border-outline-gray-2"
		>
			<TransitionGroup tag="ul" name="pending-row" class="relative divide-y divide-outline-gray-1">
				<PendingSubmission
					v-for="request in visible"
					:key="request.name"
					:request="request"
					@changed="reviewed"
					@open="open(request)"
				/>
			</TransitionGroup>
			<div ref="sentinel" aria-hidden="true" />
		</div>
		<EventDrawer v-model:open="drawer.open.value" :event="drawer.selected.value" />
	</section>
</template>

<style scoped>
/* A reviewed row leaves quickly, and the rows below slide up into its place. */
.pending-row-leave-active {
	position: absolute;
	inset-inline: 0;
	transition: opacity 150ms ease-out;
}

.pending-row-leave-to {
	opacity: 0;
}

.pending-row-move {
	transition: transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
	.pending-row-move {
		transition: none;
	}
}
</style>
