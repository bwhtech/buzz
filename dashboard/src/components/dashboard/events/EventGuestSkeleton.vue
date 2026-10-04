<script setup lang="ts">
import { Skeleton } from "frappe-ui"

// Shaped like EventGuestItem, so rows land where the placeholders stood.
withDefaults(defineProps<{ rows?: number }>(), { rows: 1 })
</script>

<template>
	<li v-for="row in rows" :key="row" class="flex items-center gap-3 px-4 py-3">
		<Skeleton class="size-7 shrink-0 rounded-full" />
		<Skeleton class="h-4 w-40 rounded-4" />
		<Skeleton class="ml-auto h-5 w-16 rounded-full" />
	</li>
</template>
