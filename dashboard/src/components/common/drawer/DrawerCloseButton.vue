<script setup lang="ts">
import { Button } from "frappe-ui"

import { useIsMobile } from "@/composables/useIsMobile"

import { DrawerClose } from "./parts"

withDefaults(defineProps<{ label?: string }>(), { label: "Close" })

const isMobile = useIsMobile()
</script>

<template>
	<DrawerClose as-child>
		<Button size="sm" :icon="isMobile ? 'lucide-x' : 'lucide-chevrons-right'" :aria-label="label" />
	</DrawerClose>
</template>
