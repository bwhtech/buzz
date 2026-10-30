<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"

import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import type { CouponItem } from "@/types"
import { accessCodeLink } from "@/utils/couponLabels"

// An access code shares as a link that unlocks its tickets; a promo code as the code itself.
const props = defineProps<{ coupon: CouponItem; registrationLink: string | null }>()

const copyToClipboard = useCopyToClipboard()
const isAccessCode = computed(() => props.coupon.coupon_type === "Access Code")
const label = computed(() => (isAccessCode.value ? "Copy link" : "Copy code"))

function copy() {
	if (!isAccessCode.value) return copyToClipboard(props.coupon.code, "Code copied")
	if (props.registrationLink)
		copyToClipboard(accessCodeLink(props.registrationLink, props.coupon.code), "Link copied")
}
</script>

<template>
	<Button
		v-if="coupon.coupon_type === 'Promo Code' || (isAccessCode && registrationLink)"
		variant="ghost"
		:icon="isAccessCode ? 'lucide-link' : 'lucide-copy'"
		:label="label"
		:tooltip="label"
		@click="copy"
	/>
</template>
