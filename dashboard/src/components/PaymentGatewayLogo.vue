<script setup lang="ts">
import { computed } from "vue"

import { usePaymentGatewayLogos } from "@/data/paymentGatewayLogos"

// The size class goes on the logo; a gateway without one renders the slot instead.
defineOptions({ inheritAttrs: false })
const props = defineProps<{ gateway: string }>()

const logos = usePaymentGatewayLogos()
const logo = computed(() => logos.data?.find((row) => row.name === props.gateway))
</script>

<template>
	<span v-if="logo" v-bind="$attrs" class="inline-flex shrink-0">
		<img :src="logo.logo" :alt="gateway" class="h-full w-auto dark:hidden" />
		<img :src="logo.logo_dark" :alt="gateway" class="hidden h-full w-auto dark:block" />
	</span>
	<slot v-else />
</template>
