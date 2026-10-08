<script setup lang="ts">
import { useCall } from "frappe-ui"
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
const title = computed(() =>
	pending.value.length === 1
		? __("1 Pending Approval Event")
		: __("{0} Pending Approval Events", [String(pending.value.length)]),
)

function reviewed() {
	queue.reload()
	emit("changed")
}
</script>

<template>
	<section v-if="pending.length" class="space-y-4 border-b pb-8">
		<div class="space-y-1">
			<h2 class="text-2xl font-semibold text-ink-gray-9">{{ title }}</h2>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						"These events aren't visible on your calendar yet. We'll let the submitter know if you approve their event.",
					)
				}}
			</p>
		</div>
		<ul class="space-y-3">
			<PendingSubmission
				v-for="request in pending"
				:key="request.name"
				:request="request"
				@changed="reviewed"
			/>
		</ul>
	</section>
</template>
