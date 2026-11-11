<script setup lang="ts">
import { ErrorMessage } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventGuestSkeleton from "@/components/dashboard/events/EventGuestSkeleton.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import RequestDrawer from "@/components/dashboard/requests/RequestDrawer.vue"
import RequestList from "@/components/dashboard/requests/RequestList.vue"
import RequestsDisabled from "@/components/dashboard/requests/RequestsDisabled.vue"
import RequestStatCards from "@/components/dashboard/requests/RequestStatCards.vue"
import RequestToolbar from "@/components/dashboard/requests/RequestToolbar.vue"
import SeatsFreedBanner from "@/components/dashboard/requests/SeatsFreedBanner.vue"
import { useRequestQueue } from "@/composables/useRequestQueue"
import { useEventDoc } from "@/data/events"
import { useEventTicketTypes } from "@/data/ticketTypes"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { RegistrationRequest, RequestType } from "@/types"
import {
	freedSeats,
	isQueueEnabled,
	matchesSearch,
	matchesTicketType,
	type RequestSort,
	sortRequests,
	ticketTypeOf,
} from "@/utils/requestQueue"
import { OPEN_VIEW, type RequestAction, type RequestView, STAT_VIEWS } from "@/utils/requestStatus"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ requestType: RequestType }>()

const eventId = useRoute().params.eventId as string
const event = useEventDoc(() => eventId)
const settings = useEventTicketTypes(eventId)
const { requests, counts, rows, viewOf, act } = useRequestQueue(eventId, props.requestType)
const waitlist = props.requestType === "Waitlist"

const view = ref<RequestView | "all">(OPEN_VIEW[props.requestType])
const search = ref("")
const ticketType = ref("")
const sort = ref<RequestSort>(waitlist ? "oldest" : "newest")

const ticketTypes = computed(() => [...new Set(rows.value.map(ticketTypeOf))].filter(Boolean))
const isFiltered = computed(() => Boolean(search.value.trim() || ticketType.value))
const matched = computed(() =>
	rows.value.filter(
		(row) => matchesSearch(row, search.value) && matchesTicketType(row, ticketType.value),
	),
)
const visible = computed(() =>
	sortRequests(
		matched.value.filter((row) => view.value === "all" || viewOf(row) === view.value),
		sort.value,
	),
)

const stats = computed(() =>
	STAT_VIEWS[props.requestType].map((stat) => ({
		...stat,
		count: rows.value.filter((row) => viewOf(row) === stat.view).length,
	})),
)

// Picking the card already in view goes back to everyone.
const pick = (picked: RequestView) => (view.value = view.value === picked ? "all" : picked)

const waiting = computed(() => rows.value.filter((row) => viewOf(row) === "waiting"))
const freed = computed(() => freedSeats(counts.data?.seats_free ?? {}, waiting.value))

const VIEW_EMPTY_STATES: Record<RequestView | "all", { title: string; description: string }> = {
	all: { title: "Nothing here yet", description: "People show up here as their status changes." },
	pending: {
		title: "No pending requests",
		description: "New requests that need your review show up here.",
	},
	awaiting: {
		title: "Nobody is awaiting payment",
		description: "Approved guests show up here until they pay.",
	},
	approved: {
		title: "No approved requests yet",
		description: "Requests you approve show up here.",
	},
	declined: { title: "No declined requests", description: "Requests you decline show up here." },
	waiting: {
		title: "Nobody is waiting",
		description: "People join once a ticket type with a seat limit sells out.",
	},
	invited: {
		title: "No invites out",
		description: "People you let in show up here until they pay.",
	},
	registered: {
		title: "Nobody registered from the waitlist yet",
		description: "People who got a seat show up here.",
	},
	expired: {
		title: "No expired invites",
		description: "Invites that weren't paid in time show up here.",
	},
	removed: {
		title: "Nobody removed",
		description: "People you remove from the waitlist show up here.",
	},
}

const filteredEmptyState = computed(() => ({
	title: waitlist ? "No matching people" : "No matching requests",
	description: search.value.trim()
		? `Nobody here matches “${search.value.trim()}”.`
		: "Nobody here matches these filters.",
}))

const isEnabled = computed(() => !settings.data || isQueueEnabled(props.requestType, settings.data))
const isQueueEmpty = computed(() => !requests.loading && !requests.error && !rows.value.length)
// An empty queue waits for the settings, to tell "not enabled" from "nothing yet".
const isLoading = computed(
	() =>
		(requests.loading && !requests.data) ||
		(isQueueEmpty.value && settings.loading && !settings.data),
)
const emptyQueueCopy = waitlist
	? {
			title: "Nobody has joined the waitlist yet",
			description: "People can join once a ticket type with a seat limit sells out.",
		}
	: {
			title: "No approval requests yet",
			description: "Registrations that need your approval show up here.",
		}

const queueIcon = waitlist ? "lucide-list-ordered" : "lucide-user-check"

// Held by name, so a reload keeps the drawer on fresh data and a decided row stays open.
const selectedName = ref<string | null>(null)
const selected = computed(() => rows.value.find((row) => row.name === selectedName.value) ?? null)
const selectedIndex = computed(() =>
	visible.value.findIndex((row) => row.name === selectedName.value),
)
const drawerOpen = computed<boolean>({
	get: () => selected.value !== null,
	set: (open) => !open && (selectedName.value = null),
})
const step = (by: number) => {
	const next = visible.value[selectedIndex.value + by]
	if (next) selectedName.value = next.name
}

// Deciding from the drawer moves on to the next request still in view.
function actFromDrawer(action: RequestAction) {
	const current = selected.value
	if (!current) return
	const index = selectedIndex.value
	act(action, [current])
	const stillShown = view.value === "all" || viewOf(current) === view.value
	if (!stillShown)
		selectedName.value = visible.value[index]?.name ?? visible.value[index - 1]?.name ?? null
}

function letIn(people: RegistrationRequest[]) {
	view.value = "waiting"
	act("approve", people)
}

const offerHours = computed(() => Number(event.doc?.payment_offer_hours || 48))
const seatsFreeFor = (row: RegistrationRequest | null) =>
	row ? (counts.data?.seats_free[ticketTypeOf(row)] ?? 0) : 0
</script>

<template>
	<EventPageHeader :title="event.doc?.title" :section="waitlist ? 'Waitlist' : 'Approvals'" />

	<PageWithSidebar>
		<EventArchivedAlert :event="eventId" />

		<ul
			v-if="isLoading"
			class="divide-y divide-outline-gray-1 overflow-hidden rounded-6 border border-outline-gray-2"
		>
			<EventGuestSkeleton :rows="5" />
		</ul>
		<ErrorMessage v-else-if="requests.error" :message="serverErrorMessage(requests.error)" />
		<RequestsDisabled
			v-else-if="isQueueEmpty && !isEnabled"
			:type="requestType"
			:event-id="eventId"
		/>
		<template v-else>
			<RequestStatCards :stats="stats" :active="view" @pick="pick" />

			<SeatsFreedBanner v-if="waitlist" :freed="freed" @let-in="letIn" />

			<section class="space-y-3">
				<RequestToolbar
					v-if="!isQueueEmpty"
					v-model:search="search"
					v-model:sort="sort"
					v-model:ticket-type="ticketType"
					:ticket-types="ticketTypes"
					:search-placeholder="waitlist ? 'Search the waitlist' : 'Search by name or email'"
				/>

				<RequestList
					v-if="visible.length"
					:type="requestType"
					:rows="visible"
					:view-of="viewOf"
					:selected-name="selectedName"
					:show-status="view === 'all'"
					@open="selectedName = $event"
					@act="act"
				/>
				<EmptyState v-else-if="isQueueEmpty" v-bind="emptyQueueCopy" :icon="queueIcon" />
				<EmptyState v-else-if="isFiltered" v-bind="filteredEmptyState" icon="lucide-filter-x" />
				<EmptyState v-else v-bind="VIEW_EMPTY_STATES[view]" :icon="queueIcon" />
			</section>
		</template>
	</PageWithSidebar>

	<RequestDrawer
		v-model:open="drawerOpen"
		:request="selected"
		:view="selected && viewOf(selected)"
		:offer-hours="offerHours"
		:seats-free="seatsFreeFor(selected)"
		:has-previous="selectedIndex > 0"
		:has-next="selectedIndex >= 0 && selectedIndex < visible.length - 1"
		@previous="step(-1)"
		@next="step(1)"
		@act="actFromDrawer"
	/>
</template>
