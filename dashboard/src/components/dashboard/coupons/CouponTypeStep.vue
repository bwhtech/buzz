<script setup lang="ts">
import { computed, watch } from "vue"

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
	{
		value: "Access Code",
		icon: "lucide-key-round",
		title: "Access code",
		description: "Unlock hidden ticket types, with an optional discount",
	},
]

const noDiscountOption: CouponOption<CouponItem["discount_type"]> = {
	value: "None",
	icon: "lucide-ticket",
	title: "No discount",
	description: "The code only unlocks the tickets",
}

const discountTypeOptions: CouponOption<CouponItem["discount_type"]>[] = [
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

const isAccessCode = computed(() => couponType.value === "Access Code")
const discountOptions = computed(() =>
	isAccessCode.value ? [noDiscountOption, ...discountTypeOptions] : discountTypeOptions,
)

// No discount only makes sense for an access code, and is its default.
watch(couponType, (type) => {
	if (type === "Access Code") discountType.value = "None"
	else if (discountType.value === "None") discountType.value = "Percentage"
})
</script>

<template>
	<div class="space-y-6">
		<CouponOptionCards v-model="couponType" label="How it's applied" :options="typeOptions" />
		<CouponOptionCards v-model="discountType" label="Discount" :options="discountOptions" />
	</div>
</template>
