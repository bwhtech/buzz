<script setup lang="ts">
import { Icon } from "frappe-ui"

import type { CouponItem, CouponTicketType } from "@/types"
import { isAccessCode, isTypedCode } from "@/utils/couponForm"
import {
	conditionLabel,
	discountLabel,
	scheduleLabel,
	scopeLabel,
	statusTheme,
	typeLabel,
	usedLabel,
} from "@/utils/couponLabels"

import CouponCopyLink from "./CouponCopyLink.vue"

defineProps<{
	coupons: CouponItem[]
	ticketTypes: CouponTicketType[]
	registrationLink: string | null
}>()
defineEmits<{ open: [name: string] }>()

const TYPE_STYLES = {
	"Promo Code": { icon: "lucide-ticket-percent", class: "text-ink-gray-7" },
	Automatic: { icon: "lucide-zap", class: "text-ink-amber-7" },
	"Access Code": { icon: "lucide-key-round", class: "text-ink-violet-7" },
}
// The solid badge shades, so the dot reads as the same status colour.
const STATUS_DOTS = {
	green: "bg-surface-green-7",
	blue: "bg-surface-blue-7",
	amber: "bg-surface-amber-7",
	gray: "bg-surface-gray-5",
}

const isDimmed = (coupon: CouponItem) => ["Disabled", "Used up"].includes(coupon.status)
const usedShare = (coupon: CouponItem) =>
	coupon.usage_limit ? Math.min(100, (coupon.times_used / coupon.usage_limit) * 100) : 0

// An access code leads with what it unlocks, so its discount moves into the details.
function details(coupon: CouponItem, ticketTypes: CouponTicketType[]) {
	const discount = isAccessCode(coupon) ? accessDiscountLabel(coupon) : null
	const scope = isAccessCode(coupon) ? null : scopeLabel(coupon, ticketTypes)
	const perBuyer = coupon.once_per_buyer ? "1 per buyer" : null
	return [discount, scope, conditionLabel(coupon), perBuyer].filter(Boolean).join(" · ")
}

const accessDiscountLabel = (coupon: CouponItem) =>
	coupon.discount_type === "None" ? "No discount" : `Plus ${discountLabel(coupon)}`
</script>

<template>
	<div class="grid grid-cols-[repeat(auto-fill,minmax(18rem,1fr))] gap-2.5">
		<div v-for="coupon in coupons" :key="coupon.name" class="relative flex">
			<button
				type="button"
				class="flex w-full flex-col rounded-5 border border-outline-gray-2 p-3.5 text-left transition-[background-color,transform] duration-150 ease-out active:scale-[0.99] [@media(hover:hover)]:hover:bg-surface-gray-1 focus-visible:focus-ring motion-reduce:transition-none"
				:class="{ 'opacity-60': isDimmed(coupon) }"
				@click="$emit('open', coupon.name)"
			>
				<span class="flex w-full items-center justify-between gap-2 text-sm">
					<span class="flex items-center gap-1.5" :class="TYPE_STYLES[coupon.coupon_type].class">
						<Icon :icon="TYPE_STYLES[coupon.coupon_type].icon" class="size-3.5 shrink-0" />
						{{ typeLabel(coupon) }}
					</span>
					<span class="flex items-center gap-1.5 text-ink-gray-7">
						<span
							class="size-1.5 rounded-full"
							:class="STATUS_DOTS[statusTheme(coupon.status)]"
							aria-hidden="true"
						/>
						{{ coupon.status }}
					</span>
				</span>

				<span
					class="mt-3 block truncate text-xl text-ink-gray-9"
					:class="[
						isTypedCode(coupon) ? 'font-mono font-bold tracking-wide' : 'font-semibold',
						{ 'pr-24': isAccessCode(coupon) },
					]"
				>
					{{ coupon.code }}
				</span>

				<span v-if="isAccessCode(coupon)" class="mt-1 flex items-center gap-1.5 text-base">
					<Icon icon="lucide-lock-open" class="size-4 shrink-0 text-ink-gray-7" />
					<span class="truncate text-ink-gray-7">
						Unlocks
						<span class="font-medium text-ink-gray-9">{{ scopeLabel(coupon, ticketTypes) }}</span>
					</span>
				</span>
				<span v-else class="mt-1 block text-base font-medium text-ink-gray-9">
					{{ discountLabel(coupon) }}
				</span>

				<span class="mt-1 block text-sm text-ink-gray-5 text-pretty">
					{{ details(coupon, ticketTypes) }}
				</span>

				<span v-if="coupon.description" class="mt-3 flex gap-1.5 text-sm text-ink-gray-7">
					<Icon icon="lucide-sticky-note" class="mt-0.5 size-3.5 shrink-0 text-ink-gray-5" />
					<span class="line-clamp-2 text-pretty">{{ coupon.description }}</span>
				</span>

				<!-- Pins the footer to the bottom of the tallest card in the row. -->
				<span class="min-h-4 flex-1" aria-hidden="true" />
				<span
					class="flex w-full items-center gap-2 border-t border-outline-gray-1 pt-3 text-xs text-ink-gray-5"
				>
					<span class="h-1 w-6 shrink-0 overflow-hidden rounded-full bg-surface-gray-2">
						<span
							class="block h-full rounded-full bg-surface-gray-7"
							:style="{ width: `${usedShare(coupon)}%` }"
						/>
					</span>
					<span class="flex-1 tabular-nums">{{ usedLabel(coupon) }}</span>
					<span>{{ scheduleLabel(coupon) }}</span>
				</span>
			</button>
			<CouponCopyLink
				v-if="isAccessCode(coupon)"
				class="absolute right-2 top-[2.65rem]"
				:code="coupon.code"
				:registration-link="registrationLink"
			/>
		</div>
	</div>
</template>
