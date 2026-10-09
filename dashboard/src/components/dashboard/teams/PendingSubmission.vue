<script setup lang="ts">
import { Badge, Button, Tooltip, dayjs, toast } from "frappe-ui"
import { computed } from "vue"

import SubmissionThumbnail from "@/components/dashboard/teams/SubmissionThumbnail.vue"
import { useIsMobile } from "@/composables/useIsMobile"
import { useReviewAction } from "@/data/communities"
import type { CommunityRequest } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ request: CommunityRequest }>()
const emit = defineEmits<{ changed: []; open: [] }>()

const isMobile = useIsMobile()

const approve = useReviewAction("approve_request")
const reject = useReviewAction("reject_request")

const when = computed(() => {
	const { start_date, start_time } = props.request
	const date = dayjs(start_date).format("ddd D MMM")
	// The server sends a time as "9:30:00", without a leading zero.
	return start_time ? `${date}, ${dayjs(`2000-01-01 ${start_time}`).format("HH:mm")}` : date
})

const submitter = computed(() => props.request.submitter_name || props.request.submitted_by || "")
const submittedAgo = computed(() => dayjs(props.request.creation).fromNow())

const details = computed(() => {
	const { place, event_team_name, event_url, is_external_event } = props.request
	const host = event_team_name && `by ${event_team_name}`
	const site =
		is_external_event && event_url && `(${new URL(event_url).hostname.replace(/^www\./, "")})`
	return [when.value, place, [host, site].filter(Boolean).join(" ")].filter(Boolean).join(" · ")
})

async function review(action: ReturnType<typeof useReviewAction>, done: string) {
	// useCall does not reject on a server error; it sets `error`.
	await action.submit({ request: props.request.name })
	if (action.error) return toast.error(serverErrorMessage(action.error))
	toast.success(done)
	emit("changed")
}
</script>

<template>
	<li class="relative flex items-center gap-3 bg-surface-base px-4 py-3 hover:bg-surface-gray-1">
		<!-- Overlay, so the row opens the event while the actions above it stay buttons. -->
		<button
			type="button"
			class="absolute inset-0 focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-outline-gray-3"
			:aria-label="__('Open {0}', [request.event_title])"
			@click="emit('open')"
		/>
		<SubmissionThumbnail :request="request" />

		<div class="min-w-0 flex-1 space-y-0.5">
			<p class="flex items-start gap-1.5 text-base font-medium text-ink-gray-8">
				<span class="line-clamp-2 min-w-0 [overflow-wrap:anywhere]" :title="request.event_title">
					{{ request.event_title }}
				</span>
				<Badge
					v-if="request.is_external_event"
					class="shrink-0"
					size="sm"
					:label="__('External')"
				/>
			</p>
			<p class="truncate text-sm text-ink-gray-5" :title="details">{{ details }}</p>
			<!-- Below lg the submitter column is gone, so the row carries it here. -->
			<p class="truncate text-sm text-ink-gray-5 lg:hidden" :title="submitter">
				{{ __("{0} · {1}", [submitter, submittedAgo]) }}
			</p>
		</div>

		<div class="hidden w-48 shrink-0 text-right text-sm lg:block">
			<p class="truncate text-ink-gray-7" :title="submitter">{{ submitter }}</p>
			<p class="text-ink-gray-5">{{ submittedAgo }}</p>
		</div>

		<div class="relative z-10 flex shrink-0 gap-1.5">
			<Tooltip :text="__('Remove')">
				<Button
					theme="red"
					variant="subtle"
					:size="isMobile ? 'lg' : 'md'"
					icon="lucide-x"
					:aria-label="__('Remove {0}', [request.event_title])"
					:loading="reject.loading"
					:disabled="approve.loading"
					@click="review(reject, __('Submission removed'))"
				/>
			</Tooltip>
			<Tooltip :text="__('Approve')">
				<Button
					theme="green"
					variant="subtle"
					:size="isMobile ? 'lg' : 'md'"
					icon="lucide-check"
					:aria-label="__('Approve {0}', [request.event_title])"
					:loading="approve.loading"
					:disabled="reject.loading"
					@click="review(approve, __('Event added to your calendar'))"
				/>
			</Tooltip>
		</div>
	</li>
</template>
