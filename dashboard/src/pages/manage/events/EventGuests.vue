<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { ErrorMessage, useList } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import { ListFilters } from "@/components/common/filters"
import CheckInZoneCards from "@/components/dashboard/events/checkin-zones/CheckInZoneCards.vue"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventGuestItem from "@/components/dashboard/events/EventGuestItem.vue"
import EventGuestSkeleton from "@/components/dashboard/events/EventGuestSkeleton.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import GuestInfoDrawer from "@/components/dashboard/events/GuestInfoDrawer.vue"
import GuestQuickActions from "@/components/dashboard/events/GuestQuickActions.vue"
import GuestStatCards from "@/components/dashboard/events/GuestStatCards.vue"
import { useDeepLinkedRecord } from "@/composables/useDeepLinkedRecord"
import { useEventGuests } from "@/composables/useEventGuests"
import { useListQuery } from "@/composables/useListQuery"
import { useCanWriteEvent, useRegistrationTrend } from "@/data/events"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { FrappeError } from "@/types"

const route = useRoute()
const eventId = route.params.eventId as string

const { search, order, conditions, isFiltered } = useListQuery()

const zone = ref("")

const { guests, fetchOne, loadMore, page, loadingFirstPage, loadingMore } = useEventGuests(
	eventId,
	search,
	order,
	conditions,
	{ zone },
)

// The export is the list on screen, not the whole event: same filters, same order.
const exportQuery = computed(() => ({
	search: search.value.trim(),
	filters: JSON.stringify(conditions.value),
	order: order.value,
	zone: zone.value,
}))

const trend = useRegistrationTrend(eventId)
const canWrite = useCanWriteEvent(eventId)

// The answers on a guest come from the registration form, so it is edited from here too.
const registrationForm = useList<{ name: string }>({
	doctype: "Buzz Form",
	filters: { event: eventId, form_doctype: "Event Booking" },
	fields: ["name"],
	limit: 1,
})

const message = (error: unknown) => (error as FrappeError | null)?.message

const selectedZone = computed(() => page.data?.zones.find((row) => row.name === zone.value) ?? null)

// The ticket is what is held, not its position. A row can be opened while a search is
// still settling, and by the time the new page lands an index points at a different guest.
// A `?guest=` link opens that ticket; one past the loaded pages has no neighbours to step to.
const { selectedId, selected: selectedGuest } = useDeepLinkedRecord({
	param: "guest",
	rows: guests,
	fetchOne,
	notFound: __("This guest isn't available"),
})

const selectedIndex = computed(() =>
	guests.value.findIndex((guest) => guest.name === selectedId.value),
)

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

		<section aria-label="Overview">
			<GuestStatCards
				:trend="trend.data"
				:guests="page.data"
				:zone="selectedZone"
				:loading="page.loading"
			/>
			<ErrorMessage :message="message(trend.error)" />
		</section>

		<section class="space-y-3">
			<h2 class="text-lg font-semibold text-ink-gray-9">Check-in zones</h2>
			<CheckInZoneCards
				v-model="zone"
				:event="eventId"
				:stats="page.data?.zones ?? []"
				:read-only="!canWrite.data?.has_permission"
				@changed="page.reload()"
			/>
		</section>

		<section class="space-y-3">
			<h2 class="text-lg font-semibold text-ink-gray-9">
				{{ selectedZone ? `Guest list · ${selectedZone.title}` : "Guest list" }}
			</h2>

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
					class="divide-y divide-outline-gray-1 overflow-hidden rounded-5 border border-outline-gray-2"
				>
					<EventGuestSkeleton :rows="6" />
				</ul>

				<div v-else-if="page.error">
					<ErrorMessage :message="message(page.error)" />
				</div>

				<div v-else>
					<ul
						v-if="guests.length"
						class="divide-y divide-outline-gray-1 overflow-hidden rounded-5 border border-outline-gray-2"
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
						icon="lucide-filter-x"
					/>
					<EmptyState
						v-else
						title="No guests yet"
						description="Guests show up here once they book a ticket."
						icon="lucide-users"
					/>

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
			<GuestQuickActions
				v-if="page.data"
				:event="eventId"
				:title="page.data.title"
				:query="exportQuery"
				:checked-in="page.data.checked_in_any_zone"
				:total="page.data.total"
				:registration-form="canWrite.data?.has_permission ? registrationForm.data?.[0]?.name : null"
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
