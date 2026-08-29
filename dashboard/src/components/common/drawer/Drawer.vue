<script setup lang="ts">
import { DrawerRoot } from "reka-ui"

// The edge the drawer is anchored to is the edge you swipe towards to dismiss it,
// so reka's swipeDirection is the only positioning input DrawerContent needs.
withDefaults(
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
</script>

<template>
	<DrawerRoot
		v-model:open="open"
		v-model:snap-point="snapPoint"
		:swipe-direction="swipeDirection"
		:modal="modal"
		:snap-points="snapPoints"
	>
		<slot />
	</DrawerRoot>
</template>
