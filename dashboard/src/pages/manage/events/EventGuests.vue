<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { useRouteQuery } from "@vueuse/router"
import { ErrorMessage } from "frappe-ui"
import { DonutChart, NumberCard } from "frappe-ui/charts"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import { FilterBar, type FilterGroup, type FilterValues } from "@/components/common/filters"
import EventGuestActions from "@/components/dashboard/events/EventGuestActions.vue"
import EventGuestItem from "@/components/dashboard/events/EventGuestItem.vue"
import EventGuestSkeleton from "@/components/dashboard/events/EventGuestSkeleton.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import GuestInfoDrawer from "@/components/dashboard/events/GuestInfoDrawer.vue"
import { type GuestOrder, useEventGuests } from "@/composables/useEventGuests"
import { useUrlFilters } from "@/composables/useUrlFilters"
import { useRegistrationTrend } from "@/data/events"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { FrappeError } from "@/types"

const route = useRoute()
const eventId = route.params.eventId as string

// Both controls sit in the query string, so a searched or re-sorted list survives a
// reload and can be handed to someone else as a link. The default order stays implicit:
// only "oldest first" is worth a param.
const filters = useUrlFilters(["order", "ticket_type"])
const searchParam = useRouteQuery<string | null>("q", null)

const search = computed<string>({
	get: () => searchParam.value ?? "",
	set: (term) => (searchParam.value = term.trim() ? term : null),
})

// Read-only: the filter bar owns the write, and routes it through `barFilters` so the
// order and the type filter land in the query string as one assignment.
const order = computed<GuestOrder>(() => (filters.value.order?.[0] === "asc" ? "asc" : "desc"))

const ticketTypes = computed(() => filters.value.ticket_type || [])

const { guests, loadMore, page, loadingFirstPage, loadingMore } = useEventGuests(
	eventId,
	search,
	order,
	ticketTypes,
)

// The export is the list on screen, not the whole event: same filters, same order.
const exportQuery = computed(() => ({
	search: search.value.trim(),
	ticket_types: ticketTypes.value.join(","),
	order: order.value,
}))

// The bar speaks in groups of chosen values; sort is one choice, so it reads and writes
// the single order the list is fetched with.
// The types come back with the guests, so the filter offers exactly what this event sells.
const filterGroups = computed<FilterGroup[]>(() => [
	{
		key: "order",
		label: "Sort by",
		quick: true,
		single: true,
		options: [
			{ value: "desc", label: "Newest first" },
			{ value: "asc", label: "Oldest first" },
		],
	},
	{
		key: "ticket_type",
		label: "Ticket type",
		options: (page.data?.ticket_types || []).map((type) => ({
			value: type.name,
			label: type.title || type.name,
		})),
	},
])

// The bar speaks in groups of chosen values, so sort travels beside the type filter and
// is unpacked back into the single order the list is fetched with.
const barFilters = computed<FilterValues>({
	get: () => ({ order: [order.value], ticket_type: ticketTypes.value }),
	// One write rather than two: the query string is the store, and a second assignment
	// would build on the value the first has not landed yet.
	set: (next) => {
		filters.value = {
			order: next.order?.[0] === "asc" ? ["asc"] : [],
			ticket_type: next.ticket_type || [],
		}
	},
})

const trend = useRegistrationTrend(eventId)

const message = (error: unknown) => (error as FrappeError | null)?.messages?.join("\n")

// echarts paints into a canvas, where a `var(--token)` never resolves, so the green is
// the palette's own 600 written out.
const REGISTRATION_GREEN = "oklch(0.57 0.119 158.092)"

// The trend arrives as one row per day and ticket type. The sparkline wants the stack's
// own height, so the types of a day are summed back together, oldest day first.
const rows = computed(() => trend.data?.per_day || [])

const perDay = computed(() => {
	const totals = new Map<string, number>()
	for (const row of rows.value) totals.set(row.date, (totals.get(row.date) || 0) + row.count)
	return [...totals.values()]
})

// All-time, like the total beside it — summing the window would split a number the card
// does not show. A tier nobody has bought is left off the ring.
const byTicketType = computed(() =>
	(trend.data?.by_ticket_type || [])
		.filter((row) => row.count)
		.map((row) => ({ ticket_type: row.ticket_type || "Unnamed", count: row.count })),
)

const showTicketTypes = computed(() => byTicketType.value.length > 1)

const sinceYesterday = computed(() => {
	const days = perDay.value
	return days.length < 2 ? null : days[days.length - 1] - days[days.length - 2]
})

// The ticket is what is held, not its position. A row can be opened while a search is
// still settling, and by the time the new page lands an index points at a different guest.
const selectedId = ref<string | null>(null)

const selectedIndex = computed(() =>
	guests.value.findIndex((guest) => guest.name === selectedId.value),
)

const selectedGuest = computed(() => guests.value[selectedIndex.value] ?? null)

const drawerOpen = computed<boolean>({
	get: () => selectedGuest.value !== null,
	set: (open) => !open && (selectedId.value = null),
})

const step = (by: number) => {
	const next = guests.value[selectedIndex.value + by]
	if (next) selectedId.value = next.name
}

// The next page is fetched when the foot of the list comes into view, a screen early so
// the rows are already there by the time the scroll reaches them.
const sentinel = ref<HTMLElement | null>(null)
useIntersectionObserver(sentinel, ([entry]) => entry?.isIntersecting && loadMore(), {
	rootMargin: "400px",
})
</script>

<template>
	<EventPageHeader :title="page.data?.title" section="Guests" />

	<PageWithSidebar>
		<section class="space-y-2">
			<h1 class="text-xl font-semibold text-ink-gray-9">How it's going</h1>

			<!-- One row of readings. The donut only earns its half when there is more than one
			 tier to split; with a single type the card takes the whole row. -->
			<div class="grid gap-4 sm:grid-cols-2">
				<NumberCard
					:class="showTicketTypes ? '' : 'sm:col-span-2'"
					title="Registered"
					:value="trend.data?.total ?? null"
					:loading="trend.loading"
					:delta="sinceYesterday"
					delta-caption="vs yesterday"
					:sparkline="{ data: perDay, type: 'line', color: REGISTRATION_GREEN }"
				/>

				<div v-if="showTicketTypes && !trend.error" class="h-64 w-full">
					<DonutChart
						title="Ticket types"
						:data="byTicketType"
						category="ticket_type"
						value="count"
						center-label="registered"
						:loading="trend.loading"
					/>
				</div>
			</div>

			<ErrorMessage :message="message(trend.error)" />
		</section>

		<section class="space-y-3">
			<h2 class="text-xl font-semibold text-ink-gray-9">Guest list</h2>

			<FilterBar
				v-model="barFilters"
				v-model:search="search"
				searchable
				search-placeholder="Search by name or email"
				:groups="filterGroups"
			/>

			<!-- Announced rather than only drawn: typing changes the list silently otherwise. -->
			<p
				v-if="search.trim() || ticketTypes.length"
				aria-live="polite"
				class="text-sm text-ink-gray-5"
			>
				{{ page.data?.matched ?? 0 }} of {{ page.data?.total ?? 0 }} guests
			</p>

			<Transition
				mode="out-in"
				enter-active-class="transition-opacity duration-150 ease-out motion-reduce:transition-none"
				enter-from-class="opacity-0"
				leave-active-class="transition-opacity duration-100 ease-out motion-reduce:transition-none"
				leave-to-class="opacity-0"
			>
				<!-- Rows shaped like the real ones, so the list settles into place instead of
				 shoving the page down when it arrives. -->
				<ul
					v-if="loadingFirstPage"
					class="divide-y divide-outline-gray-1 overflow-hidden rounded-7 border border-outline-gray-2"
				>
					<EventGuestSkeleton :rows="6" />
				</ul>

				<div v-else-if="page.error">
					<ErrorMessage :message="message(page.error)" />
				</div>

				<div v-else>
					<ul
						v-if="guests.length"
						class="divide-y divide-outline-gray-1 overflow-hidden rounded-7 border border-outline-gray-2"
					>
						<EventGuestItem
							v-for="guest in guests"
							:key="guest.name"
							:guest="guest"
							:selected="guest.name === selectedId"
							@open="selectedId = guest.name"
						/>
						<!-- The next page draws itself into the list rather than announcing itself
						 under it: the rows arrive where the placeholders already are. -->
						<EventGuestSkeleton v-if="loadingMore" :rows="3" />
					</ul>

					<p v-else-if="search" class="text-base text-ink-gray-5">
						Nobody here matches “{{ search }}”.
					</p>
					<p v-else-if="ticketTypes.length" class="text-base text-ink-gray-5">
						Nobody holds one of these ticket types.
					</p>
					<p v-else class="text-base text-ink-gray-5">No guests yet.</p>

					<div ref="sentinel" aria-hidden="true" />

					<!-- The list has a floor, so the scroll ends on a statement rather than on
					 rows that might still be coming. The label sits on the rule rather than
					 beside it, which reads as a stop instead of another section heading. -->
					<div
						v-if="guests.length && !page.data?.has_next_page && !loadingMore"
						class="relative mt-6 flex justify-center"
					>
						<span
							class="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-surface-gray-2"
							aria-hidden="true"
						/>
						<p
							class="relative bg-surface-elevation-1 px-4 py-1 text-xs italic text-ink-gray-4 font-serif"
						>
							End of list
						</p>
					</div>
				</div>
			</Transition>
		</section>
		<template #sidebar>
			<EventGuestActions
				v-if="page.data"
				:event="eventId"
				:title="page.data.title"
				:registration-link="page.data.registration_link"
				:closed="!!page.data.registrations_closed"
				:can-write="!!page.data.can_write"
				:query="exportQuery"
				@changed="page.reload()"
			/>
		</template>
	</PageWithSidebar>

	<GuestInfoDrawer
		v-model:open="drawerOpen"
		:guest="selectedGuest"
		:event="page.data"
		:has-previous="selectedIndex > 0"
		:has-next="selectedIndex >= 0 && selectedIndex < guests.length - 1"
		@previous="step(-1)"
		@next="step(1)"
	/>
</template>
