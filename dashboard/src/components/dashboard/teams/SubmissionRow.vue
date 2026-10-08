<script setup lang="ts">
import { Avatar, Button, dayjs, toast } from "frappe-ui"

import { useReviewAction } from "@/data/communities"
import type { CommunityRequest } from "@/types"
import { eventUrl } from "@/utils/eventUrl"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ request: CommunityRequest; canReview: boolean }>()
const emit = defineEmits<{ changed: [] }>()

const approve = useReviewAction("approve_request")
const reject = useReviewAction("reject_request")
const remove = useReviewAction("remove_event")

async function run(action: ReturnType<typeof useReviewAction>, done: string) {
	try {
		await action.submit({ request: props.request.name })
		toast.success(__(done))
		emit("changed")
	} catch (error) {
		toast.error(serverErrorMessage(error))
	}
}
</script>

<template>
	<li class="flex items-center gap-3 border-b py-3">
		<Avatar
			shape="square"
			size="lg"
			:image="request.event_team_logo ?? undefined"
			:label="request.event_team_name"
		/>
		<div class="min-w-0 flex-1">
			<a
				v-if="request.event_route"
				:href="eventUrl(request.event_route)"
				target="_blank"
				rel="noopener"
				class="block truncate text-base font-medium text-ink-gray-8 hover:underline"
			>
				{{ request.event_title }}
			</a>
			<span v-else class="block truncate text-base font-medium text-ink-gray-8">
				{{ request.event_title }}
			</span>
			<p class="truncate text-sm text-ink-gray-5">
				{{ request.event_team_name }} · {{ dayjs(request.start_date).format("D MMM YYYY") }}
				<template v-if="request.submitter_name"> · {{ request.submitter_name }}</template>
			</p>
		</div>
		<div v-if="canReview" class="flex shrink-0 gap-2">
			<template v-if="request.status === 'Pending'">
				<Button
					:label="__('Reject')"
					variant="ghost"
					:loading="reject.loading"
					@click="run(reject, 'Submission rejected')"
				/>
				<Button
					:label="__('Approve')"
					variant="subtle"
					:loading="approve.loading"
					@click="run(approve, 'Event listed on your page')"
				/>
			</template>
			<Button
				v-else
				:label="__('Remove')"
				variant="ghost"
				:loading="remove.loading"
				@click="run(remove, 'Event removed from your page')"
			/>
		</div>
	</li>
</template>
