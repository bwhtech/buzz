<template>
	<div class="overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-base">
		<div class="flex items-center justify-between gap-2 px-4 pb-1.5 pt-3.5">
			<h3 class="text-base-semibold text-ink-gray-9">{{ __("Payment") }}</h3>
			<Badge v-if="(booking.total_amount || 0) > 0" variant="subtle" :theme="paymentBadge.theme">
				<template #prefix>
					<component :is="paymentBadge.icon" class="size-3" />
				</template>
				{{ paymentBadge.label }}
			</Badge>
		</div>

		<div class="flex flex-col gap-2 px-4 pb-3 pt-1.5 text-p-sm text-ink-gray-6 tabular-nums">
			<!-- Net Amount (hide when tax-inclusive and no discount) -->
			<div v-if="!isTaxInclusive || hasDiscount" class="flex justify-between gap-3">
				<span>{{ __("Subtotal") }}</span>
				<span>{{ formatPrice(booking.net_amount || 0, booking.currency || "INR") }}</span>
			</div>

			<div v-if="booking.coupon_code" class="flex justify-between gap-3">
				<span>{{ __("Coupon") }}</span>
				<span>{{ booking.coupon_code }}</span>
			</div>

			<div v-if="hasDiscount" class="flex justify-between gap-3">
				<span>{{ __("Discount") }}</span>
				<span>-{{ formatPrice(booking.discount_amount, booking.currency || "INR") }}</span>
			</div>

			<!-- Tax Information (exclusive only) -->
			<div v-if="hasTax && !isTaxInclusive" class="flex justify-between gap-3">
				<span>{{ __(booking.tax_label || "Tax") }} ({{ booking.tax_percentage || 0 }}%)</span>
				<span>{{ formatPrice(booking.tax_amount || 0, booking.currency || "INR") }}</span>
			</div>
		</div>

		<div class="border-t border-outline-gray-1 px-4 py-3">
			<div class="flex items-baseline justify-between gap-3 text-ink-gray-9">
				<span class="text-base-semibold">{{ isPaid ? __("Total paid") : __("Total") }}</span>
				<span class="text-lg-semibold tabular-nums">
					{{ formatPrice(booking.total_amount || 0, booking.currency || "INR") }}
				</span>
			</div>
			<p v-if="hasTax && isTaxInclusive" class="mt-1 text-right text-p-xs text-ink-gray-5">
				{{
					__("Inclusive of {0} {1} ({2}%)", [
						formatPrice(booking.tax_amount || 0, booking.currency || "INR"),
						__(booking.tax_label || "Tax"),
						booking.tax_percentage || 0,
					])
				}}
			</p>
		</div>

		<div
			v-if="$slots.footer"
			class="border-t border-outline-gray-1 bg-surface-gray-1 px-4 py-2.5 text-p-xs text-ink-gray-5"
		>
			<slot name="footer" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Badge } from "frappe-ui"
import { computed } from "vue"
import LucideCheck from "~icons/lucide/check"
import LucideClock from "~icons/lucide/clock"
import LucideX from "~icons/lucide/x"

import { formatPrice } from "@/utils/currency"

const props = defineProps({
	booking: {
		type: Object,
		required: true,
		validator: (value) => {
			return typeof value === "object" && value !== null
		},
	},
})

const hasTax = computed(() => {
	return Boolean(props.booking.tax_amount && props.booking.tax_amount > 0)
})

const hasDiscount = computed(() => {
	return (props.booking.discount_amount || 0) > 0
})

const isPaid = computed(() => props.booking.payment_status === "Paid")

const paymentBadge = computed(() => {
	const status = props.booking.payment_status
	if (status === "Paid") {
		return { label: __("Paid"), theme: "green" as const, icon: LucideCheck }
	} else if (status === "Verification Pending") {
		return {
			label: __("Verification Pending"),
			theme: "amber" as const,
			icon: LucideClock,
		}
	}
	return { label: __(status || "Unpaid"), theme: "red" as const, icon: LucideX }
})

const isTaxInclusive = computed(() => {
	// Tax-inclusive: total_amount equals net_amount minus discount (tax not added on top)
	if (!hasTax.value) return false
	const expected = (props.booking.net_amount || 0) - (props.booking.discount_amount || 0)
	return Math.abs(props.booking.total_amount - expected) < 0.01
})
</script>
