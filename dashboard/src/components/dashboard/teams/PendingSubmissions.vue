<script setup lang="ts">
import { Badge, useCall } from "frappe-ui"
import { computed, watch } from "vue"

import PendingSubmission from "@/components/dashboard/teams/PendingSubmission.vue"
import type { CommunityQueue } from "@/types"

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

function reviewed() {
	queue.reload()
	emit("changed")
}
</script>

<template>
	<section v-if="pending.length" class="space-y-4 border-b border-outline-gray-2 pb-8">
		<div class="space-y-1">
			<h2 class="flex items-center gap-2 text-xl font-semibold text-ink-gray-9">
				{{ __("Pending Approval") }}
				<Badge :label="String(pending.length)" size="md" />
			</h2>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						"These events aren't on your calendar yet. They show up once you approve them, and we let the submitter know.",
					)
				}}
			</p>
		</div>
		<TransitionGroup tag="ul" name="pending-row" class="relative space-y-3">
			<PendingSubmission
				v-for="request in pending"
				:key="request.name"
				:request="request"
				@changed="reviewed"
			/>
		</TransitionGroup>
	</section>
</template>

<style scoped>
/* A reviewed row leaves quickly, and the rows below slide up into its place. */
.pending-row-leave-active {
	position: absolute;
	inset-inline: 0;
	transition:
		opacity 150ms ease-out,
		transform 150ms ease-out;
}

.pending-row-leave-to {
	opacity: 0;
	transform: scale(0.98);
}

.pending-row-move {
	transition: transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
	.pending-row-leave-active,
	.pending-row-move {
		transition: opacity 150ms ease-out;
	}

	.pending-row-leave-to {
		transform: none;
	}
}
</style>
