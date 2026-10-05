<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { ErrorMessage, Icon, Skeleton } from "frappe-ui"
import { DonutChart, NumberCard } from "frappe-ui/charts"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import { ListFilters } from "@/components/common/filters"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import EventTalkActions from "@/components/dashboard/proposals/EventTalkActions.vue"
import EventTalkProposalDrawer from "@/components/dashboard/proposals/EventTalkProposalDrawer.vue"
import ProposalCard from "@/components/dashboard/proposals/ProposalCard.vue"
import { useEventProposals } from "@/composables/useEventProposals"
import { useListQuery } from "@/composables/useListQuery"
import { useProposalTrend } from "@/data/proposals"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { FrappeError, ProposalWithEvent } from "@/types"

const route = useRoute()
const eventId = route.params.eventId as string

const { search, order, conditions, isFiltered } = useListQuery()

const { proposals, applyStatus, loadMore, page, loadingFirstPage, loadingMore } = useEventProposals(
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

const trend = useProposalTrend(eventId)

const message = (error: unknown) => (error as FrappeError | null)?.message

// echarts paints into a canvas, where a `var(--token)` never resolves, so the violet is
// the palette's own 600 written out.
const PROPOSAL_VIOLET = "oklch(0.54 0.245 292.717)"

const perDay = computed(() => (trend.data?.per_day || []).map((day) => day.count))

// A status nobody has used is left off the ring.
const byStatus = computed(() =>
	(trend.data?.by_status || []).filter((row) => row.count).map((row) => ({ ...row })),
)

const showStatuses = computed(() => byStatus.value.length > 1)

const sinceYesterday = computed(() => {
	const days = perDay.value
	return days.length < 2 ? null : days[days.length - 1] - days[days.length - 2]
})

// The proposal is what is held, not its position. A card can be opened while a search is
// still settling, and by the time the new page lands an index points at a different talk.
const selectedId = ref<string | null>(null)

const selected = computed(
	() => proposals.value.find((proposal) => proposal.name === selectedId.value) ?? null,
)

const drawerOpen = computed<boolean>({
	get: () => selected.value !== null,
	set: (open) => !open && (selectedId.value = null),
})

// The row is patched rather than refetched — see applyStatus. The card above counts the
// whole pipeline, so it is the one thing that does have to go back to the server.
const onStatusChanged = (status: string) => {
	if (selectedId.value) applyStatus(selectedId.value, status)
	trend.reload()
}

// The next page is fetched when the foot of the list comes into view, a screen early so
// the cards are already there by the time the scroll reaches them.
const sentinel = ref<HTMLElement | null>(null)
useIntersectionObserver(sentinel, ([entry]) => entry?.isIntersecting && loadMore(), {
	rootMargin: "400px",
})
</script>

<template>
	<EventPageHeader :title="page.data?.title" section="Talks" />

	<PageWithSidebar>
		<EventArchivedAlert :event="eventId" />

		<section class="space-y-2">
			<h1 class="text-xl font-semibold text-ink-gray-9">How it's going</h1>

			<!-- One row of readings. The donut only earns its half when more than one status
				 is in play; with a single one the card takes the whole row. -->
			<div class="grid gap-4 sm:grid-cols-2">
				<NumberCard
					:class="showStatuses ? '' : 'sm:col-span-2'"
					title="Proposals"
					:value="trend.data?.total ?? null"
					:loading="trend.loading"
					:delta="sinceYesterday"
					delta-caption="vs yesterday"
					:sparkline="{ data: perDay, type: 'line', color: PROPOSAL_VIOLET }"
				/>

				<div v-if="showStatuses && !trend.error" class="status-donut h-64 w-full">
					<DonutChart
						title="Review status"
						:data="byStatus"
						category="status"
						value="count"
						center-label="proposals"
						:loading="trend.loading"
					/>
				</div>
			</div>

			<ErrorMessage :message="message(trend.error)" />
		</section>

		<section class="space-y-3">
			<h2 class="text-xl font-semibold text-ink-gray-9">Talks</h2>

			<ListFilters
				v-model="conditions"
				v-model:search="search"
				v-model:order="order"
				:fields="page.data?.filter_fields ?? []"
				search-placeholder="Search by title or speaker"
			/>

			<!-- Announced rather than only drawn: typing changes the list silently otherwise. -->
			<p v-if="isFiltered" aria-live="polite" class="text-sm text-ink-gray-5">
				{{ page.data?.matched ?? 0 }} of {{ page.data?.total ?? 0 }} proposals
			</p>

			<Transition
				mode="out-in"
				enter-active-class="transition-opacity duration-150 ease-out motion-reduce:transition-none"
				enter-from-class="opacity-0"
				leave-active-class="transition-opacity duration-100 ease-out motion-reduce:transition-none"
				leave-to-class="opacity-0"
			>
				<!-- Cards shaped like the real ones, so the list settles into place instead of
					 shoving the page down when it arrives. -->
				<div v-if="loadingFirstPage" class="space-y-3">
					<Skeleton v-for="row in 4" :key="row" class="h-[7.5rem] w-full rounded-8" />
				</div>

				<div v-else-if="page.error">
					<ErrorMessage :message="message(page.error)" />
				</div>

				<div v-else>
					<div v-if="proposals.length" class="space-y-3">
						<ProposalCard
							v-for="proposal in proposals"
							:key="proposal.name"
							:proposal="proposal as ProposalWithEvent"
							:show-event="false"
							@open="selectedId = proposal.name"
						/>
						<Skeleton v-if="loadingMore" class="h-[7.5rem] w-full rounded-8" />
					</div>

					<EmptyState
						v-else-if="isFiltered"
						title="No matching talks"
						:description="
							search.trim()
								? `No talk here matches “${search.trim()}”.`
								: 'No talk here matches these filters.'
						"
					>
						<template #illustration>
							<Icon name="lucide-filter-x" class="size-5 text-ink-gray-5" />
						</template>
					</EmptyState>
					<EmptyState
						v-else
						title="No talks yet"
						description="Proposals submitted through the call for proposals show up here."
					>
						<template #illustration>
							<Icon name="lucide-mic" class="size-5 text-ink-gray-5" />
						</template>
					</EmptyState>

					<div ref="sentinel" aria-hidden="true" />

					<!-- The list has a floor, so the scroll ends on a statement rather than on
						 cards that might still be coming. -->
					<div
						v-if="proposals.length && !page.data?.has_next_page && !loadingMore"
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
			<EventTalkActions
				v-if="page.data"
				:event="eventId"
				:title="page.data.title"
				:proposal-link="page.data.proposal_link"
				:closed="!!page.data.proposals_closed"
				:can-write="!!page.data.can_write"
				:query="exportQuery"
				@changed="page.reload()"
			/>
		</template>
	</PageWithSidebar>

	<EventTalkProposalDrawer
		v-model:open="drawerOpen"
		:proposal="selected"
		:can-write="page.data?.can_write"
		@changed="onStatusChanged"
	/>
</template>

<style scoped>
/* DonutChart renders its legend whenever there is more than one slice, with no prop to
   turn it off. Seven statuses make a wrapping row taller than the ring it explains; the
   tooltip still names every slice. */
.status-donut :deep([data-slot="chart-legend"]) {
	display: none;
}
</style>
