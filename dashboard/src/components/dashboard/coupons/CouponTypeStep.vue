<script setup lang="ts">
import type { CouponItem } from "@/types"

import CouponOptionCards, { type CouponOption } from "./CouponOptionCards.vue"

const couponType = defineModel<CouponItem["coupon_type"]>("couponType", { required: true })
const discountType = defineModel<CouponItem["discount_type"]>("discountType", { required: true })

const typeOptions: CouponOption<CouponItem["coupon_type"]>[] = [
	{
		value: "Promo Code",
		icon: "lucide-ticket-percent",
		title: "Promo code",
		description: "Participants enter a code at checkout",
	},
	{
		value: "Automatic",
		icon: "lucide-zap",
		title: "Automatic",
		description: "Applies on its own when an order qualifies",
	},
]

const discountOptions: CouponOption<CouponItem["discount_type"]>[] = [
	{
		value: "Percentage",
		icon: "lucide-percent",
		title: "Percentage",
		description: "A share of the order, like 20% off",
	},
	{
		value: "Flat Amount",
		icon: "lucide-banknote",
		title: "Fixed amount",
		description: "Set per currency, like ₹500 off",
	},
]
</script>

<template>
	<div class="space-y-6">
		<CouponOptionCards v-model="couponType" label="How it's applied" :options="typeOptions" />
		<CouponOptionCards v-model="discountType" label="Discount" :options="discountOptions" />
	</div>
</template>
