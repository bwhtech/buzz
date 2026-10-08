<script setup lang="ts">
import { Button, dayjs, toast } from "frappe-ui"
import { computed } from "vue"

import { useReviewAction } from "@/data/communities"
import type { CommunityRequest } from "@/types"
import { eventUrl } from "@/utils/eventUrl"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ request: CommunityRequest }>()
const emit = defineEmits<{ changed: [] }>()

const approve = useReviewAction("approve_request")
const reject = useReviewAction("reject_request")

const when = computed(() => {
	const { start_date, start_time } = props.request
	const date = dayjs(start_date).format("ddd D MMM")
	// The server sends a time as "9:30:00", without a leading zero.
	return start_time ? `${date}, ${dayjs(`2000-01-01 ${start_time}`).format("HH:mm")}` : date
})
// A Buzz event opens its own page; an external one, the platform it lives on.
const link = computed(() =>
	props.request.event_route ? eventUrl(props.request.event_route) : props.request.event_url,
)
const submitter = computed(() => {
	const { submitter_name, submitted_by } = props.request
	return submitter_name && submitter_name !== submitted_by
		? `${submitter_name} (${submitted_by})`
		: submitted_by
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
	<li class="flex items-start gap-4 rounded-6 border border-outline-gray-2 p-4">
		<div class="min-w-0 flex-1 space-y-1">
			<component
				:is="link ? 'a' : 'span'"
				:href="link || undefined"
				:target="link ? '_blank' : undefined"
				rel="noopener"
				class="flex items-center gap-1.5 text-lg font-semibold text-ink-gray-9"
				:class="{ 'hover:underline': link }"
			>
				<span class="truncate">{{ request.event_title }}</span>
				<span
					v-if="link"
					class="lucide-square-arrow-out-up-right size-4 shrink-0 text-ink-gray-5"
				/>
			</component>
			<p class="text-base text-ink-gray-6">
				{{ [when, request.place].filter(Boolean).join(" · ") }}
			</p>
			<p v-if="submitter" class="text-sm text-ink-gray-5">
				{{ __("Submitted by {0}", [submitter]) }}
			</p>
		</div>
		<div class="flex shrink-0 gap-2">
			<Button
				variant="ghost"
				icon-left="lucide-x"
				:label="__('Remove')"
				:loading="reject.loading"
				:disabled="approve.loading"
				@click="review(reject, __('Submission removed'))"
			/>
			<Button
				variant="subtle"
				icon-left="lucide-check"
				:label="__('Approve')"
				:loading="approve.loading"
				:disabled="reject.loading"
				@click="review(approve, __('Event added to your calendar'))"
			/>
		</div>
	</li>
</template>
