<script setup lang="ts">
import { useIntersectionObserver } from "@vueuse/core"
import { ErrorMessage, Icon, Skeleton } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import { ListFilters } from "@/components/common/filters"
import SectionHeader from "@/components/common/SectionHeader.vue"
import EnquiryRow from "@/components/dashboard/sponsorships/EnquiryRow.vue"
import { useEventEnquiries } from "@/composables/useEventEnquiries"
import { useListQuery } from "@/composables/useListQuery"
import type { FrappeError } from "@/types"

const props = defineProps<{ event: string }>()
defineEmits<{ open: [enquiry: string] }>()

const { search, order, conditions, isFiltered } = useListQuery()

const { enquiries, applyStatus, loadMore, page, loadingFirstPage, loadingMore } = useEventEnquiries(
	props.event,
	search,
	order,
	conditions,
)

defineExpose({ applyStatus, reload: page.reload })

const errorMessage = computed(() => (page.error as FrappeError | null)?.message)

// The next page loads a screen before the foot of the list scrolls into view.
const sentinel = ref<HTMLElement | null>(null)
useIntersectionObserver(sentinel, ([entry]) => entry?.isIntersecting && loadMore(), {
	rootMargin: "400px",
})
</script>

<template>
	<section class="space-y-3">
		<SectionHeader title="Enquiries" :count="page.data?.total" />

		<ListFilters
			v-model="conditions"
			v-model:search="search"
			v-model:order="order"
			:fields="page.data?.filter_fields ?? []"
			search-placeholder="Search by company, email or website"
		/>

		<p v-if="isFiltered" aria-live="polite" class="text-sm text-ink-gray-5">
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
			v-else-if="isFiltered"
			title="No matching enquiries"
			:description="
				search.trim()
					? `No enquiry matches “${search.trim()}”.`
					: 'No enquiry matches these filters.'
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
