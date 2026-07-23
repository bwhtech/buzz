<!-- BookingSummary.vue -->
<template>
	<div class="bg-surface-gray-1 border border-outline-gray-1 rounded-lg p-4">
		<h2 class="text-2xl-bold text-ink-gray-9 mb-4">{{ __("Booking Summary") }}</h2>

		<!-- Tickets Section -->
		<div v-if="Object.keys(summary.tickets).length" class="mb-4">
			<h3 class="text-lg-semibold text-ink-gray-8 mb-2">{{ __("Tickets") }}</h3>
			<div
				v-for="(ticket, name) in summary.tickets"
				:key="name"
				class="flex justify-between items-start text-ink-gray-7 mb-2"
			>
				<div class="flex flex-col">
					<span>{{ __(ticket.title) }}</span>
					<span
						v-if="freeTicketType === name && freeTicketCount > 0"
						class="text-sm text-ink-gray-5"
					>
						{{ Math.min(freeTicketCount, ticket.count) }} x
						<span class="line-through">{{
							formatPriceOrFree(ticket.price, ticket.currency)
						}}</span>
						{{ __("Free")
						}}{{
							ticket.count > freeTicketCount
								? `, ${ticket.count - freeTicketCount} x ${formatPriceOrFree(
										ticket.price,
										ticket.currency
								  )}`
								: ""
						}}
					</span>
					<span v-else-if="netAmount > 0" class="text-sm text-ink-gray-5">
						{{ ticket.count }} x {{ formatPriceOrFree(ticket.price, ticket.currency) }}
					</span>
					<span v-else class="text-sm text-ink-gray-5">x {{ ticket.count }}</span>
				</div>
				<span v-if="freeTicketType === name && freeTicketCount > 0" class="font-medium">
					{{
						ticket.count <= freeTicketCount
							? __("Free")
							: formatPriceOrFree(
									(ticket.count - freeTicketCount) * ticket.price,
									ticket.currency
							  )
					}}
				</span>
				<span v-else-if="netAmount > 0" class="font-medium">{{
					formatPriceOrFree(ticket.amount, ticket.currency)
				}}</span>
			</div>
		</div>

		<!-- Add-ons Section -->
		<div v-if="Object.keys(summary.add_ons).length" class="mb-4">
			<h3 class="text-lg-semibold text-ink-gray-8 mb-2">{{ __("Add-ons") }}</h3>
			<div
				v-for="(addOn, name) in summary.add_ons"
				:key="name"
				class="flex justify-between items-start text-ink-gray-7 mb-2"
			>
				<div class="flex flex-col">
					<span>{{ __(addOn.title) }}</span>
					<span v-if="freeAddOnCounts[name] > 0" class="text-sm text-ink-gray-5">
						{{ Math.min(freeAddOnCounts[name], addOn.count) }} x
						<span class="line-through">{{
							formatPriceOrFree(addOn.price, addOn.currency)
						}}</span>
						{{ __("Free")
						}}{{
							addOn.count > freeAddOnCounts[name]
								? `, ${addOn.count - freeAddOnCounts[name]} x ${formatPriceOrFree(
										addOn.price,
										addOn.currency
								  )}`
								: ""
						}}
					</span>
					<span v-else-if="netAmount > 0" class="text-sm text-ink-gray-5">
						{{ addOn.count }} x {{ formatPriceOrFree(addOn.price, addOn.currency) }}
					</span>
					<span v-else class="text-sm text-ink-gray-5">x {{ addOn.count }}</span>
				</div>
				<span v-if="freeAddOnCounts[name] > 0" class="font-medium">
					{{
						addOn.count <= freeAddOnCounts[name]
							? __("Free")
							: formatPriceOrFree(
									(addOn.count - freeAddOnCounts[name]) * addOn.price,
									addOn.currency
							  )
					}}
				</span>
				<span v-else-if="netAmount > 0" class="font-medium">{{
					formatPriceOrFree(addOn.amount, addOn.currency)
				}}</span>
			</div>
		</div>

		<!-- Show pricing summary if total > 0 OR coupon made it free -->
		<template v-if="total > 0 || (couponApplied && netAmount > 0)">
			<hr class="my-4 border-t border-outline-gray-1" />

			<!-- Subtotal (hide when tax-inclusive and no discount, since it equals total) -->
			<div
				v-if="!taxInclusive || (couponApplied && discountAmount > 0)"
				class="flex justify-between items-center text-ink-gray-7 mb-2"
			>
				<span>{{ __("Subtotal") }}</span>
				<span class="font-medium">{{ formatPriceOrFree(netAmount, totalCurrency) }}</span>
			</div>

			<!-- Discount Section -->
			<div
				v-if="couponApplied && discountAmount > 0"
				class="flex justify-between items-center text-green-600 mb-2"
			>
				<span>{{
					couponType === "Free Tickets" ? __("Free Tickets") : __("Discount")
				}}</span>
				<span class="font-medium"
					>-{{ formatPriceOrFree(discountAmount, totalCurrency) }}</span
				>
			</div>

			<!-- Tax Section (exclusive only — shown as line item added to total) -->
			<div
				v-if="shouldApplyTax && !taxInclusive"
				class="flex justify-between items-center text-ink-gray-7 mb-2"
			>
				<span>{{ __(taxLabel) }} ({{ taxPercentage }}%)</span>
				<span class="font-medium">{{ formatPriceOrFree(taxAmount, totalCurrency) }}</span>
			</div>

			<!-- Final Total Section -->
			<hr v-if="shouldApplyTax" class="my-2 border-t border-outline-gray-1" />
			<div class="flex justify-between items-center text-2xl-bold text-ink-gray-9">
				<h3>{{ __("Total") }}</h3>
				<span>{{ formatPriceOrFree(total, totalCurrency) }}</span>
			</div>

			<!-- Tax-inclusive note (shown below total) -->
			<div
				v-if="shouldApplyTax && taxInclusive"
				class="text-sm text-ink-gray-5 text-right mt-3"
			>
				{{
					__("Inclusive of {0} {1} ({2}%)", [
						formatPriceOrFree(taxAmount, totalCurrency),
						__(taxLabel),
						taxPercentage,
					])
				}}
			</div>
		</template>

		<!-- Free event message -->
		<template v-else>
			<hr class="my-2 border-t border-outline-gray-1" />
			<div class="text-center pt-2">
				<div class="text-2xl-bold text-green-600">{{ __("Free Event") }}</div>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { formatPriceOrFree } from "@/utils/currency";

defineProps({
	summary: {
		type: Object,
		required: true,
	},
	netAmount: {
		type: Number,
		required: true,
	},
	discountAmount: {
		type: Number,
		default: 0,
	},
	couponApplied: {
		type: Boolean,
		default: false,
	},
	couponType: {
		type: String,
		default: "",
	},
	freeAddOnCounts: {
		type: Object,
		default: () => ({}),
	},
	freeTicketType: {
		type: String,
		default: "",
	},
	freeTicketCount: {
		type: Number,
		default: 0,
	},
	taxAmount: {
		type: Number,
		default: 0,
	},
	taxPercentage: {
		type: Number,
		default: 0,
	},
	taxLabel: {
		type: String,
		default: "Tax",
	},
	taxInclusive: {
		type: Boolean,
		default: false,
	},
	shouldApplyTax: {
		type: Boolean,
		default: false,
	},
	total: {
		type: Number,
		required: true,
	},
	totalCurrency: {
		type: String,
		default: "INR",
	},
});
</script>
