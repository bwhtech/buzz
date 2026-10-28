<script setup lang="ts">
import { Icon } from "frappe-ui"
import { computed } from "vue"

import type { CouponTicketType } from "@/types"
import type { CouponValues } from "@/utils/couponForm"
import { amountsLabel, discountLabel } from "@/utils/couponLabels"

const props = defineProps<{ values: CouponValues; ticketTypes: CouponTicketType[] }>()

const unlocked = computed(() =>
	props.ticketTypes.filter((ticketType) => props.values.ticket_types.includes(ticketType.name)),
)
const code = computed(() => props.values.code.trim().toUpperCase() || "YOURCODE")
const hasDiscount = computed(() => props.values.discount_type !== "None")

const priceLabel = (ticketType: CouponTicketType) =>
	ticketType.prices.some((row) => row.price > 0) ? amountsLabel(ticketType.prices) : "Free"
</script>

<template>
	<p v-if="!unlocked.length" class="text-sm text-ink-gray-5">
		Pick a hidden ticket type to preview the booking page.
	</p>

	<div v-else class="space-y-3">
		<p class="text-xs text-ink-gray-5">Booking page preview</p>

		<div
			class="overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-elevation-1 shadow-sm"
		>
			<div class="flex flex-col gap-2.5 p-3.5 text-sm">
				<div class="flex h-[30px] items-center gap-1.5 rounded-3 bg-surface-gray-2 pl-2.5 pr-1.5">
					<Icon icon="lucide-key-round" class="size-3.5 shrink-0 text-ink-gray-5" />
					<span
						class="flex-1 truncate font-mono text-xs font-semibold tracking-wider text-ink-gray-9"
					>
						{{ code }}
					</span>
					<span class="text-xs text-ink-green-7">Unlocked</span>
				</div>

				<div
					v-for="ticketType in unlocked"
					:key="ticketType.name"
					class="flex items-center gap-2 rounded-4 border border-outline-gray-2 px-3 py-2.5"
				>
					<Icon icon="lucide-lock-open" class="size-3.5 shrink-0 text-ink-gray-5" />
					<span class="flex-1 truncate text-ink-gray-8">{{ ticketType.title }}</span>
					<span class="tabular-nums text-ink-gray-6">{{ priceLabel(ticketType) }}</span>
				</div>

				<p v-if="hasDiscount" class="text-ink-green-7">{{ discountLabel(values) }} at checkout</p>
			</div>
		</div>

		<p class="text-xs text-ink-gray-5 text-pretty">
			Participants without the code don't see these tickets.
		</p>
	</div>
</template>
