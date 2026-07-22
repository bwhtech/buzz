<template>
	<div class="bg-surface-elevation-1 border border-outline-gray-1 rounded-lg p-6">
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-lg-semibold text-ink-gray-9">{{ __("Payment Summary") }}</h3>
			<Badge
				v-if="(booking.total_amount || 0) > 0"
				variant="subtle"
				:theme="paymentBadge.theme"
				size="sm"
			>
				<template #prefix>
					<component :is="paymentBadge.icon" class="w-3 h-3" />
				</template>
				{{ paymentBadge.label }}
			</Badge>
		</div>

		<div class="space-y-3">
			<!-- Net Amount (hide when tax-inclusive and no discount) -->
			<div
				v-if="!isTaxInclusive || hasDiscount"
				class="flex justify-between items-center text-ink-gray-7"
			>
				<span>{{ __("Subtotal") }}</span>
				<span class="font-medium">{{
					formatPrice(booking.net_amount || 0, booking.currency || "INR")
				}}</span>
			</div>

			<!-- Coupon Code -->
			<div
				v-if="booking.coupon_code"
				class="flex justify-between items-center text-ink-gray-7"
			>
				<span>{{ __("Coupon") }}</span>
				<span class="font-medium text-green-600">{{ booking.coupon_code }}</span>
			</div>

			<!-- Discount -->
			<div v-if="hasDiscount" class="flex justify-between items-center text-green-600">
				<span>{{ __("Discount") }}</span>
				<span class="font-medium"
					>-{{ formatPrice(booking.discount_amount, booking.currency || "INR") }}</span
				>
			</div>

			<!-- Tax Information (exclusive only) -->
			<div
				v-if="hasTax && !isTaxInclusive"
				class="flex justify-between items-center text-ink-gray-7"
			>
				<span
					>{{ __(booking.tax_label || "Tax") }} ({{
						booking.tax_percentage || 0
					}}%)</span
				>
				<span class="font-medium">{{
					formatPrice(booking.tax_amount || 0, booking.currency || "INR")
				}}</span>
			</div>

			<!-- Divider -->
			<hr class="border-outline-gray-1" />

			<!-- Total Amount -->
			<div class="flex justify-between items-center text-lg-semibold text-ink-gray-9">
				<span>{{ isPaid ? __("Total Paid") : __("Total") }}</span>
				<span :class="isPaid ? 'text-ink-green-5' : 'text-ink-gray-9'">{{
					formatPrice(booking.total_amount || 0, booking.currency || "INR")
				}}</span>
			</div>

			<!-- Tax-inclusive note -->
			<div v-if="hasTax && isTaxInclusive" class="text-sm text-ink-gray-5 text-right mt-3">
				{{
					__("Inclusive of {0} {1} ({2}%)", [
						formatPrice(booking.tax_amount || 0, booking.currency || "INR"),
						__(booking.tax_label || "Tax"),
						booking.tax_percentage || 0,
					])
				}}
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { formatPrice } from "@/utils/currency";
import { Badge } from "frappe-ui";
import { computed } from "vue";
import LucideCheck from "~icons/lucide/check";
import LucideClock from "~icons/lucide/clock";
import LucideX from "~icons/lucide/x";

const props = defineProps({
	booking: {
		type: Object,
		required: true,
		validator: (value) => {
			return typeof value === "object" && value !== null;
		},
	},
});

const hasTax = computed(() => {
	return Boolean(props.booking.tax_amount && props.booking.tax_amount > 0);
});

const hasDiscount = computed(() => {
	return (props.booking.discount_amount || 0) > 0;
});

const isPaid = computed(() => props.booking.payment_status === "Paid");

const paymentBadge = computed(() => {
	const status = props.booking.payment_status;
	if (status === "Paid") {
		return { label: __("Paid"), theme: "green" as const, icon: LucideCheck };
	} else if (status === "Verification Pending") {
		return {
			label: __("Verification Pending"),
			theme: "orange" as const,
			icon: LucideClock,
		};
	}
	return { label: __(status || "Unpaid"), theme: "red" as const, icon: LucideX };
});

const isTaxInclusive = computed(() => {
	// Tax-inclusive: total_amount equals net_amount minus discount (tax not added on top)
	if (!hasTax.value) return false;
	const expected = (props.booking.net_amount || 0) - (props.booking.discount_amount || 0);
	return Math.abs(props.booking.total_amount - expected) < 0.01;
});
</script>
