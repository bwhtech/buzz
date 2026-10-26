<script setup lang="ts">
import { Button, ErrorMessage, Icon, Skeleton, TabButtons } from "frappe-ui"
import { NumberCard } from "frappe-ui/charts"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import ListSection from "@/components/common/ListSection.vue"
import CouponCards from "@/components/dashboard/coupons/CouponCards.vue"
import CouponDrawer from "@/components/dashboard/coupons/CouponDrawer.vue"
import CouponRows from "@/components/dashboard/coupons/CouponRows.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import { useIsMobile } from "@/composables/useIsMobile"
import { useEventCoupons } from "@/data/coupons"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { FrappeError } from "@/types"
import { couponStats } from "@/utils/couponLabels"

const eventId = useRoute().params.eventId as string

const page = useEventCoupons(eventId)

const isMobile = useIsMobile()

type Filter = "all" | "Promo Code" | "Automatic" | "Access Code"
const filter = ref<Filter>("all")
const FILTERS: { label: string; value: Filter }[] = [
	{ label: "All", value: "all" },
	{ label: "Codes", value: "Promo Code" },
	{ label: "Automatic", value: "Automatic" },
	{ label: "Access codes", value: "Access Code" },
]
const matchesFilter = (coupon: { coupon_type: string }, value: Filter) =>
	value === "all" || coupon.coupon_type === value
// Phones show how many each filter holds, as the list has no column of counts to glance at.
const filterOptions = computed(() =>
	FILTERS.map((option) => {
		const count = (page.data?.coupons ?? []).filter((coupon) =>
			matchesFilter(coupon, option.value),
		).length
		return isMobile.value ? { ...option, label: `${option.label} ${count}` } : option
	}),
)

const hasCoupons = computed(() => !!page.data?.coupons.length)
const stats = computed(() =>
	page.data ? couponStats(page.data.coupons, page.data.discounted) : [],
)
const coupons = computed(() =>
	(page.data?.coupons ?? []).filter((coupon) => matchesFilter(coupon, filter.value)),
)

const drawerOpen = ref(false)
// Held by name so a reload keeps the drawer pointing at fresh data; null is a new coupon.
const selectedName = ref<string | null>(null)
const selectedCoupon = computed(
	() => page.data?.coupons.find((coupon) => coupon.name === selectedName.value) ?? null,
)

function openCoupon(name: string | null) {
	selectedName.value = name
	drawerOpen.value = true
}

const message = (error: unknown) => (error as FrappeError | null)?.message
</script>

<template>
	<EventPageHeader :title="page.data?.title" section="Coupons" />

	<PageWithSidebar>
		<div v-if="page.loading && !page.data" class="space-y-3">
			<Skeleton class="h-6 w-24" />
			<Skeleton v-for="row in 3" :key="row" class="h-10 w-full rounded-4" />
		</div>

		<ErrorMessage v-else-if="page.error" :message="message(page.error)" />

		<div v-else-if="page.data" class="space-y-6">
			<!-- The last card takes the row on phones: it can carry an amount per currency. -->
			<div v-if="hasCoupons" class="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4">
				<NumberCard
					v-for="stat in stats"
					:key="stat.label"
					class="last:max-sm:col-span-2"
					:title="stat.label"
					:value="stat.value"
				/>
			</div>

			<ListSection
				title="Coupons & Access Codes"
				description="Discounts participants redeem with a code, or that apply on their own when an order qualifies, and codes that unlock hidden tickets"
				:count="hasCoupons ? page.data.coupons.length : null"
				:empty="!hasCoupons"
				empty-title="No coupons yet"
				empty-description="Create a code participants enter at checkout, or a discount that applies automatically"
				empty-icon="lucide-ticket-percent"
				:empty-action="
					page.data.can_write
						? { label: 'Create coupon', iconLeft: 'lucide-plus', onClick: () => openCoupon(null) }
						: null
				"
			>
				<template v-if="hasCoupons" #toolbar>
					<div class="flex items-center gap-2">
						<TabButtons v-model="filter" :options="filterOptions" />
						<Button
							v-if="page.data.can_write && !isMobile"
							class="ml-auto"
							variant="outline"
							icon-left="lucide-plus"
							label="Add"
							@click="openCoupon(null)"
						/>
					</div>
				</template>

				<CouponRows
					v-if="isMobile"
					:coupons="coupons"
					:ticket-types="page.data.ticket_types"
					:registration-link="page.data.registration_link"
					@open="openCoupon"
				/>
				<CouponCards
					v-else
					:coupons="coupons"
					:ticket-types="page.data.ticket_types"
					:registration-link="page.data.registration_link"
					@open="openCoupon"
				/>
				<!-- Room to scroll the last row clear of the floating button. -->
				<div v-if="isMobile" class="h-14" aria-hidden="true" />
			</ListSection>
		</div>

		<template v-if="hasCoupons && page.data?.registration_link && !isMobile" #sidebar>
			<a
				:href="page.data.registration_link"
				target="_blank"
				rel="noopener"
				class="flex items-center gap-2 rounded-3 px-2 py-1.5 text-base text-ink-gray-8 hover:bg-surface-gray-2"
			>
				<Icon icon="lucide-arrow-up-right" class="size-4 text-ink-gray-5" />
				Preview checkout
			</a>
		</template>
	</PageWithSidebar>

	<div
		v-if="isMobile && hasCoupons && page.data?.can_write"
		class="pointer-events-none fixed inset-x-4 bottom-20 z-20 flex justify-end"
	>
		<Button
			class="pointer-events-auto shadow-lg transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.97] motion-reduce:transition-none"
			variant="solid"
			size="lg"
			icon-left="lucide-plus"
			label="New coupon"
			@click="openCoupon(null)"
		/>
	</div>

	<CouponDrawer
		v-model:open="drawerOpen"
		:event="eventId"
		:coupon="selectedCoupon"
		:ticket-types="page.data?.ticket_types ?? []"
		:can-write="!!page.data?.can_write"
		@changed="page.reload()"
	/>
</template>
