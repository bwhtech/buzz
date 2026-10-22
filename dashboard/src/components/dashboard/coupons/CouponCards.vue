<script setup lang="ts">
import { Badge, Icon, Progress } from "frappe-ui"

import type { CouponItem, CouponTicketType } from "@/types"
import {
	conditionLabel,
	discountLabel,
	endsLabel,
	scopeLabel,
	statusLabel,
	statusTheme,
	usedLabel,
} from "@/utils/couponLabels"

defineProps<{ coupons: CouponItem[]; ticketTypes: CouponTicketType[] }>()
defineEmits<{ open: [name: string] }>()

const isCode = (coupon: CouponItem) => coupon.coupon_type === "Promo Code"
const isDimmed = (coupon: CouponItem) => ["Disabled", "Used up"].includes(coupon.status)
const usedShare = (coupon: CouponItem) =>
	coupon.usage_limit ? Math.min(100, (coupon.times_used / coupon.usage_limit) * 100) : 0
const meta = (coupon: CouponItem, ticketTypes: CouponTicketType[]) =>
	[scopeLabel(coupon, ticketTypes), conditionLabel(coupon)].filter(Boolean).join(" · ")
</script>

<template>
	<div class="grid grid-cols-[repeat(auto-fill,minmax(15.5rem,1fr))] gap-2.5">
		<button
			v-for="coupon in coupons"
			:key="coupon.name"
			type="button"
			class="flex flex-col gap-3.5 rounded-5 border border-outline-gray-2 p-3.5 text-left transition-[box-shadow,border-color,transform] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.99] [@media(hover:hover)]:hover:border-outline-gray-1 [@media(hover:hover)]:hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 motion-reduce:transition-none"
			:class="{ 'opacity-60': isDimmed(coupon) }"
			@click="$emit('open', coupon.name)"
		>
			<span class="flex w-full items-center justify-between gap-2">
				<span
					v-if="isCode(coupon)"
					class="inline-flex h-6 min-w-0 items-center truncate rounded-2 border border-dashed border-outline-gray-4 bg-surface-gray-1 px-2 font-mono text-sm font-semibold tracking-wide text-ink-gray-9"
				>
					{{ coupon.code }}
				</span>
				<span
					v-else
					class="inline-flex h-6 items-center gap-1.5 rounded-2 bg-surface-amber-1 px-2 text-sm font-medium text-ink-amber-7"
				>
					<Icon icon="lucide-zap" class="size-3 shrink-0" />
					Automatic
				</span>
				<Badge :theme="statusTheme(coupon.status)" :label="statusLabel(coupon)" />
			</span>

			<span class="block">
				<span class="block text-2xl font-semibold tracking-tight text-ink-gray-9">{{
					discountLabel(coupon)
				}}</span>
				<span class="mt-1 block text-sm text-ink-gray-5 text-pretty">{{
					meta(coupon, ticketTypes)
				}}</span>
				<span
					v-if="coupon.description"
					class="mt-2 line-clamp-2 text-sm text-ink-gray-7 text-pretty"
				>
					{{ coupon.description }}
				</span>
			</span>

			<span class="mt-auto flex w-full flex-col gap-1.5">
				<Progress :value="usedShare(coupon)" size="md" />
				<span class="flex justify-between text-xs text-ink-gray-5">
					<span class="tabular-nums">{{ usedLabel(coupon) }}</span>
					<span>{{ endsLabel(coupon) }}</span>
				</span>
			</span>
		</button>
	</div>
</template>
