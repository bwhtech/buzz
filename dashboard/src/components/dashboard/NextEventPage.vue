<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import type { ManagerNavItem } from "@/utils/managerNavigation"

// The sidebar's items, already filtered to what the user may open.
const props = defineProps<{ items: ManagerNavItem[] }>()

const route = useRoute()

const nextItem = computed(() => {
	if (!route.params.eventId || route.meta.fullScreen) return undefined
	const index = props.items.findIndex((item) => item.to === route.path)
	return index < 0 ? undefined : props.items[index + 1]
})
</script>

<template>
	<nav
		v-if="nextItem"
		:aria-label="__('Next page')"
		class="mx-auto flex w-full max-w-5xl justify-end px-4 pb-8"
	>
		<Button
			variant="ghost"
			icon-right="lucide-arrow-right"
			:route="nextItem.to"
			:label="__('Next: {0}', [__(nextItem.label)])"
		/>
	</nav>
</template>
