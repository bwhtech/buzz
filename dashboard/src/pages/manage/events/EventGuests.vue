<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { ErrorMessage, Icon } from "frappe-ui"
import { DonutChart, NumberCard } from "frappe-ui/charts"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import { ListFilters } from "@/components/common/filters"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventGuestItem from "@/components/dashboard/events/EventGuestItem.vue"
import EventGuestSkeleton from "@/components/dashboard/events/EventGuestSkeleton.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import GuestInfoDrawer from "@/components/dashboard/events/GuestInfoDrawer.vue"
import GuestListExport from "@/components/dashboard/events/GuestListExport.vue"
import { useEventGuests } from "@/composables/useEventGuests"
import { useListQuery } from "@/composables/useListQuery"
import { useRegistrationTrend } from "@/data/events"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { FrappeError } from "@/types"

const route = useRoute()
const eventId = route.params.eventId as string

const { search, order, conditions, isFiltered } = useListQuery()

const { guests, loadMore, page, loadingFirstPage, loadingMore } = useEventGuests(
	eventId,
	search,
	order,
	conditions,
)

// The export is the list on screen, not the whole event: same filters, same order.
const exportQuery = computed(() => ({
	search: search.value.trim(),
	filters: JSON.stringify(conditions.value),
	order: order.value,
}))

const trend = useRegistrationTrend(eventId)

const message = (error: unknown) => (error as FrappeError | null)?.message

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
		<EventArchivedAlert :event="eventId" />

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

			<ListFilters
				v-model="conditions"
				v-model:search="search"
				v-model:order="order"
				:fields="page.data?.filter_fields ?? []"
				search-placeholder="Search by name or email"
			/>

			<!-- Announced rather than only drawn: typing changes the list silently otherwise. -->
			<p v-if="isFiltered" aria-live="polite" class="text-sm text-ink-gray-5">
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

					<EmptyState
						v-else-if="isFiltered"
						title="No matching guests"
						:description="
							search.trim()
								? `Nobody here matches “${search.trim()}”.`
								: 'Nobody here matches these filters.'
						"
					>
						<template #illustration>
							<Icon name="lucide-filter-x" class="size-5 text-ink-gray-5" />
						</template>
					</EmptyState>
					<EmptyState
						v-else
						title="No guests yet"
						description="Guests show up here once they book a ticket."
					>
						<template #illustration>
							<Icon name="lucide-users" class="size-5 text-ink-gray-5" />
						</template>
					</EmptyState>

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
			<GuestListExport
				v-if="page.data"
				:event="eventId"
				:title="page.data.title"
				:query="exportQuery"
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
