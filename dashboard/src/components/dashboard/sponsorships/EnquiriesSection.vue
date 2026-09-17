<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { useRouteQuery } from "@vueuse/router"
import { ErrorMessage, Icon, Skeleton } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import { FilterBar, type FilterGroup, type FilterValues } from "@/components/common/filters"
import SectionHeader from "@/components/common/SectionHeader.vue"
import EnquiryRow from "@/components/dashboard/sponsorships/EnquiryRow.vue"
import { ENQUIRY_STATUSES } from "@/components/dashboard/sponsorships/helpers"
import { useEventEnquiries } from "@/composables/useEventEnquiries"
import { useUrlFilters } from "@/composables/useUrlFilters"
import type { FrappeError } from "@/types"

const props = defineProps<{ event: string }>()
defineEmits<{ open: [enquiry: string] }>()

// Held in the query string, like the Talks and Guests lists, so a filtered view survives a reload.
const filters = useUrlFilters(["order", "status"])
const searchParam = useRouteQuery<string | null>("q", null)

const search = computed<string>({
	get: () => searchParam.value ?? "",
	set: (term) => (searchParam.value = term.trim() ? term : null),
})
const order = computed<"asc" | "desc">(() => (filters.value.order?.[0] === "asc" ? "asc" : "desc"))
const statuses = computed(() => filters.value.status || [])
const filtering = computed(() => Boolean(search.value.trim() || statuses.value.length))

const filterGroups: FilterGroup[] = [
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
		key: "status",
		label: "Status",
		options: ENQUIRY_STATUSES.map((value) => ({ value, label: value })),
	},
]

const barFilters = computed<FilterValues>({
	get: () => ({ order: [order.value], status: statuses.value }),
	set: (next) => {
		filters.value = {
			order: next.order?.[0] === "asc" ? ["asc"] : [],
			status: next.status || [],
		}
	},
})

const { enquiries, applyStatus, loadMore, page, loadingFirstPage, loadingMore } = useEventEnquiries(
	props.event,
	search,
	order,
	statuses,
)

defineExpose({ applyStatus, reload: page.reload })

const errorMessage = computed(() => (page.error as FrappeError | null)?.messages?.join("\n"))

// The next page loads a screen before the foot of the list scrolls into view.
const sentinel = ref<HTMLElement | null>(null)
useIntersectionObserver(sentinel, ([entry]) => entry?.isIntersecting && loadMore(), {
	rootMargin: "400px",
})
</script>

<template>
	<section class="space-y-3">
		<SectionHeader title="Enquiries" :count="page.data?.total" />

		<FilterBar
			v-model="barFilters"
			v-model:search="search"
			searchable
			search-placeholder="Search by company, email or website"
			:groups="filterGroups"
		/>

		<p v-if="filtering" aria-live="polite" class="text-sm text-ink-gray-5">
			{{ page.data?.matched ?? 0 }} of {{ page.data?.total ?? 0 }} enquiries
		</p>

		<div v-if="loadingFirstPage" class="space-y-2">
			<Skeleton v-for="row in 3" :key="row" class="h-12 w-full rounded-4" />
		</div>
		<ErrorMessage v-else-if="errorMessage" :message="errorMessage" />
		<ul v-else-if="enquiries.length" class="space-y-2">
			<EnquiryRow
				v-for="enquiry in enquiries"
				:key="enquiry.name"
				:enquiry="enquiry"
				@open="$emit('open', enquiry.name)"
			/>
			<li v-if="loadingMore"><Skeleton class="h-12 w-full rounded-4" /></li>
		</ul>
		<EmptyState
			v-else-if="filtering"
			title="No matching enquiries"
			:description="
				search.trim()
					? `No enquiry matches “${search.trim()}”.`
					: 'No enquiry sits at one of these statuses.'
			"
		>
			<template #illustration>
				<Icon name="lucide-filter-x" class="size-5 text-ink-gray-5" />
			</template>
		</EmptyState>
		<EmptyState
			v-else
			title="No enquiries yet"
			description="Enquiries submitted through the sponsorship form show up here."
		>
			<template #illustration>
				<Icon name="lucide-inbox" class="size-5 text-ink-gray-5" />
			</template>
		</EmptyState>
		<div ref="sentinel" aria-hidden="true" />
	</section>
</template>
