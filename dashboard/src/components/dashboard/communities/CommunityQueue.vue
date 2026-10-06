<script setup lang="ts">
import { watchDebounced } from "@vueuse/core"
import { Button, Combobox, Dialog, ErrorMessage, Textarea, dialog, toast } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import CommunityRequestRow from "@/components/dashboard/communities/CommunityRequestRow.vue"
import CreateEventHeader from "@/components/dashboard/CreateEventHeader.vue"
import {
	addEvent,
	approveRequest,
	rejectRequest,
	removeEvent,
	useAddableEvents,
	useCommunityQueue,
} from "@/data/communities"
import type { CommunityRequest } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ community: string; communityName: string }>()

const queue = useCommunityQueue(props.community)

const searchText = ref("")
const debouncedSearch = ref("")
watchDebounced(searchText, (text) => (debouncedSearch.value = text), { debounce: 250 })
const addableEvents = useAddableEvents(props.community, () => debouncedSearch.value)
const eventToAdd = ref<string | null>(null)
const eventOptions = computed(() =>
	(addableEvents.data || []).map((event) => ({
		label: event.title,
		value: event.name,
		description: event.team_name,
	})),
)

const rejecting = ref<CommunityRequest | null>(null)
const rejectNote = ref("")

const error = computed(() => approveRequest.error || addEvent.error)

async function refresh(message: string) {
	toast.success(message)
	await Promise.all([queue.reload(), addableEvents.reload()])
}

async function approve(request: CommunityRequest) {
	await approveRequest.submit({ request: request.name }).catch(() => null)
	if (!approveRequest.error) await refresh(__("{0} is now listed", [request.event_title]))
}

function openReject(request: CommunityRequest) {
	rejectNote.value = ""
	rejecting.value = request
}

async function reject() {
	const request = rejecting.value!
	await rejectRequest
		.submit({ request: request.name, note: rejectNote.value.trim() || null })
		.catch(() => null)
	if (rejectRequest.error) return
	rejecting.value = null
	await refresh(__("{0} was not approved", [request.event_title]))
}

function confirmRemove(request: CommunityRequest) {
	dialog.confirm({
		title: __("Remove {0}", [request.event_title]),
		message: __("The event leaves the community page. Its team can submit it again."),
		theme: "red",
		confirmLabel: __("Remove"),
		onConfirm: async () => {
			await removeEvent.submit({ request: request.name })
			// useCall settles either way, so the failure has to be rethrown to reach the dialog.
			if (removeEvent.error) throw removeEvent.error
			await refresh(__("{0} was removed", [request.event_title]))
		},
	})
}

async function add() {
	await addEvent.submit({ community: props.community, event: eventToAdd.value }).catch(() => null)
	if (addEvent.error) return
	eventToAdd.value = null
	await refresh(__("Event added"))
}
</script>

<template>
	<div class="m-auto w-full max-w-[720px] space-y-10 px-4 py-8">
		<header class="space-y-1">
			<h1 class="text-2xl font-semibold text-ink-gray-9">{{ __("Event requests") }}</h1>
			<p class="text-p-base text-ink-gray-5">
				{{ __("Events from other teams show on {0}'s page once approved.", [communityName]) }}
			</p>
		</header>

		<ErrorMessage v-if="queue.error" :message="serverErrorMessage(queue.error)" />
		<ErrorMessage :message="serverErrorMessage(error)" />

		<section class="space-y-3">
			<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">
				{{ __("Waiting for review") }}
			</h2>
			<ul v-if="queue.data?.pending.length" class="divide-y divide-outline-gray-1">
				<CommunityRequestRow
					v-for="request in queue.data.pending"
					:key="request.name"
					:request="request"
				>
					<Button :label="__('Reject')" @click="openReject(request)" />
					<Button
						variant="solid"
						:label="__('Approve')"
						:loading="approveRequest.loading"
						@click="approve(request)"
					/>
				</CommunityRequestRow>
			</ul>
			<EmptyState
				v-else-if="queue.data"
				:title="__('Nothing to review')"
				:description="__('Events other teams submit to this community land here.')"
			/>
		</section>

		<section class="space-y-3">
			<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">
				{{ __("Listed") }}
			</h2>
			<div class="flex gap-2">
				<Combobox
					v-model="eventToAdd"
					v-model:query="searchText"
					class="min-w-0 flex-1"
					:options="eventOptions"
					:loading="addableEvents.loading"
					:placeholder="__('Add an upcoming event from another team')"
				/>
				<Button
					:label="__('Add')"
					:disabled="!eventToAdd"
					:loading="addEvent.loading"
					@click="add"
				/>
			</div>
			<ul v-if="queue.data?.approved.length" class="divide-y divide-outline-gray-1">
				<CommunityRequestRow
					v-for="request in queue.data.approved"
					:key="request.name"
					:request="request"
				>
					<Button variant="ghost" :label="__('Remove')" @click="confirmRemove(request)" />
				</CommunityRequestRow>
			</ul>
		</section>
	</div>

	<Dialog
		:model-value="Boolean(rejecting)"
		:title="__('Reject {0}', [rejecting?.event_title])"
		@update:model-value="(open: boolean) => !open && (rejecting = null)"
	>
		<div class="space-y-4">
			<Textarea
				v-model="rejectNote"
				:label="__('Note to the team (optional)')"
				:rows="3"
				:placeholder="__('Why it does not fit this community')"
			/>
			<ErrorMessage :message="serverErrorMessage(rejectRequest.error)" />
			<Button
				variant="solid"
				theme="red"
				class="w-full"
				:label="__('Reject')"
				:loading="rejectRequest.loading"
				@click="reject"
			/>
		</div>
	</Dialog>
</template>
