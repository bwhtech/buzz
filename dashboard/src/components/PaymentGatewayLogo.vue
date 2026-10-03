<script setup lang="ts">
import { computed } from "vue"

import { paymentGatewayLogo } from "@/utils/paymentGateways"

// The size class goes on the logo; a gateway without one renders the slot instead.
defineOptions({ inheritAttrs: false })
const props = defineProps<{ gateway: string }>()

const logo = computed(() => paymentGatewayLogo(props.gateway))
</script>

<template>
	<span v-if="logo" v-bind="$attrs" class="inline-flex shrink-0">
		<img :src="logo.light" :alt="gateway" class="h-full w-auto dark:hidden" />
		<img :src="logo.dark" :alt="gateway" class="hidden h-full w-auto dark:block" />
	</span>
	<slot v-else />
</template>
