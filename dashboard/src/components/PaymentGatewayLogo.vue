<script setup lang="ts">
import { computed } from "vue"

import { paymentGatewayLogo } from "@/utils/paymentGateways"

// Size it through the root's height class; renders nothing for a gateway without a logo.
const props = defineProps<{ gateway: string; alt?: string }>()

const logo = computed(() => paymentGatewayLogo(props.gateway))
</script>

<template>
	<span v-if="logo" class="inline-flex shrink-0">
		<img :src="logo.light" :alt="alt ?? gateway" class="h-full w-auto dark:hidden" />
		<img :src="logo.dark" :alt="alt ?? gateway" class="hidden h-full w-auto dark:block" />
	</span>
</template>
