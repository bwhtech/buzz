<script setup lang="ts">
import { Badge, Button, Combobox, ErrorMessage, dialog, toast } from "frappe-ui"
import { computed, ref } from "vue"

import { resubmitRequest, submitEvent, useEventRequests, withdrawRequest } from "@/data/communities"
import type { CommunityRequest } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ event: string; isPublished: boolean }>()

const REQUEST_STATUS_THEMES = { Pending: "amber", Approved: "green", Rejected: "red" } as const

const requests = useEventRequests(props.event)
const community = ref<string | null>(null)

const communityOptions = computed(() =>
	(requests.data?.communities || []).map((option) => ({
		label: option.team_name,
		value: option.name,
	})),
)

// With no communities on the site and no requests, the section has nothing to offer.
const hasCommunities = computed(() =>
	Boolean(requests.data?.requests.length || requests.data?.communities.length),
)

const error = computed(() => submitEvent.error || resubmitRequest.error || withdrawRequest.error)

async function submit() {
	await submitEvent.submit({ event: props.event, community: community.value }).catch(() => null)
	if (submitEvent.error) return
	community.value = null
	toast.success(__("Sent for review"))
	await requests.reload()
}

async function resubmit(request: CommunityRequest) {
	await resubmitRequest.submit({ request: request.name }).catch(() => null)
	if (resubmitRequest.error) return
	toast.success(__("Sent for review again"))
	await requests.reload()
}

function confirmWithdraw(request: CommunityRequest) {
	dialog.confirm({
		title: __("Withdraw from {0}", [request.community_name]),
		message: __("The request is deleted. An approved event leaves the community page."),
		theme: "red",
		confirmLabel: __("Withdraw"),
		onConfirm: async () => {
			await withdrawRequest.submit({ request: request.name })
			// useCall settles either way, so the failure has to be rethrown to reach the dialog.
			if (withdrawRequest.error) throw withdrawRequest.error
			await requests.reload()
		},
	})
}
</script>

<template>
	<section v-if="hasCommunities" class="space-y-3">
		<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">
			{{ __("Communities") }}
		</h2>

		<ul v-if="requests.data?.requests.length" class="space-y-3">
			<li v-for="request in requests.data.requests" :key="request.name" class="space-y-1">
				<div class="flex items-center gap-2">
					<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">
						{{ request.community_name }}
					</span>
					<Badge :theme="REQUEST_STATUS_THEMES[request.status]" :label="__(request.status)" />
					<Button
						v-if="request.status === 'Rejected'"
						variant="ghost"
						:label="__('Resubmit')"
						:loading="resubmitRequest.loading"
						@click="resubmit(request)"
					/>
					<Button
						variant="ghost"
						icon="lucide-x"
						:aria-label="__('Withdraw from {0}', [request.community_name])"
						@click="confirmWithdraw(request)"
					/>
				</div>
				<p v-if="request.review_note" class="text-p-sm text-ink-gray-5">
					{{ request.review_note }}
				</p>
			</li>
		</ul>

		<p v-if="!isPublished" class="text-p-sm text-ink-gray-5">
			{{ __("Publish the event to submit it to a community.") }}
		</p>
		<template v-else-if="communityOptions.length">
			<p v-if="!requests.data?.requests.length" class="text-p-sm text-ink-gray-5">
				{{ __("A community lists approved events from other teams on its page.") }}
			</p>
			<div class="flex gap-2">
				<Combobox
					v-model="community"
					class="min-w-0 flex-1"
					:options="communityOptions"
					:placeholder="__('Choose a community')"
				/>
				<Button
					:label="__('Submit')"
					:disabled="!community"
					:loading="submitEvent.loading"
					@click="submit"
				/>
			</div>
		</template>

		<ErrorMessage :message="serverErrorMessage(error)" />
	</section>
</template>
