<script setup lang="ts">
import { DrawerRoot } from "reka-ui"
import { computed } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"

// The edge the drawer is anchored to is the edge you swipe towards to dismiss it,
// so reka's swipeDirection is the only positioning input DrawerContent needs.
const props = withDefaults(
	defineProps<{
		swipeDirection?: "up" | "right" | "down" | "left"
		// false lets the page stay interactive; "trap-focus" keeps focus in without
		// locking scroll.
		modal?: boolean | "trap-focus"
		snapPoints?: (number | string)[]
	}>(),
	{ swipeDirection: "down", modal: true, snapPoints: undefined },
)

const open = defineModel<boolean>("open", { default: false })
const snapPoint = defineModel<number | string | null>("snapPoint", { default: null })

// A side panel on a phone is a sliver beside a sliver of page, so it rises as a sheet.
const isMobile = useIsMobile()
const direction = computed(() => (isMobile.value ? "down" : props.swipeDirection))
</script>

<template>
	<DrawerRoot
		v-model:open="open"
		v-model:snap-point="snapPoint"
		:swipe-direction="direction"
		:modal="modal"
		:snap-points="snapPoints"
	>
		<slot />
	</DrawerRoot>
</template>
