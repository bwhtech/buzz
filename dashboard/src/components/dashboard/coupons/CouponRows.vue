<script setup lang="ts">
import { Icon } from "frappe-ui"

import type { CouponItem, CouponTicketType } from "@/types"
import { isTypedCode } from "@/utils/couponForm"
import { discountLabel, scopeLabel, statusLabel, typeLabel, usedLabel } from "@/utils/couponLabels"

import CouponCopyButton from "./CouponCopyButton.vue"

defineProps<{
	coupons: CouponItem[]
	ticketTypes: CouponTicketType[]
	registrationLink: string | null
}>()
defineEmits<{ open: [name: string] }>()

const isCode = isTypedCode
const ICONS = {
	"Promo Code": "lucide-ticket-percent",
	Automatic: "lucide-zap",
	"Access Code": "lucide-key-round",
}
const isDimmed = (coupon: CouponItem) => ["Disabled", "Used up"].includes(coupon.status)
</script>

<template>
	<ul class="divide-y divide-outline-gray-1 overflow-hidden rounded-4 border border-outline-gray-2">
		<li v-for="coupon in coupons" :key="coupon.name" class="flex items-center">
			<button
				type="button"
				class="flex min-h-14 min-w-0 flex-1 items-center gap-3 px-3 py-2.5 text-left transition-colors duration-150 active:bg-surface-gray-1"
				@click="$emit('open', coupon.name)"
			>
				<span
					class="flex size-9 shrink-0 items-center justify-center rounded-3 bg-surface-gray-2 text-ink-gray-6"
				>
					<Icon :icon="ICONS[coupon.coupon_type]" class="size-4" />
				</span>
				<span class="min-w-0 flex-1" :class="{ 'opacity-60': isDimmed(coupon) }">
					<span class="flex items-center gap-2">
						<span
							class="min-w-0 flex-1 truncate text-base text-ink-gray-9"
							:class="isCode(coupon) ? 'font-mono font-semibold tracking-wide' : 'font-medium'"
						>
							{{ coupon.code }}
						</span>
						<span class="shrink-0 text-sm font-semibold text-ink-gray-9">{{
							discountLabel(coupon)
						}}</span>
					</span>
					<span class="mt-0.5 flex items-center gap-2 text-sm text-ink-gray-5">
						<span class="min-w-0 flex-1 truncate">
							{{ typeLabel(coupon) }} · {{ scopeLabel(coupon, ticketTypes) }} ·
							{{ usedLabel(coupon) }}
						</span>
						<span class="flex shrink-0 items-center gap-1.5">
							<span
								class="size-1.5 rounded-full"
								:class="{
									'bg-surface-green-6': coupon.status === 'Active',
									'bg-surface-blue-6': coupon.status === 'Scheduled',
									'bg-surface-gray-5': !['Active', 'Scheduled'].includes(coupon.status),
								}"
							/>
							{{ statusLabel(coupon) }}
						</span>
					</span>
				</span>
			</button>
			<CouponCopyButton class="mr-2" :coupon="coupon" :registration-link="registrationLink" />
		</li>
	</ul>
</template>
