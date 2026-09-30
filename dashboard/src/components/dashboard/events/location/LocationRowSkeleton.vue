<script setup lang="ts">
import { Skeleton } from "frappe-ui"

defineProps<{ label: string }>()
</script>

<template>
	<!-- The shape of three rows, so the list does not jump when the real ones arrive. -->
	<div aria-busy="true">
		<span class="sr-only">{{ label }}</span>
		<div v-for="row in 3" :key="row" class="flex gap-2 px-2 py-1.5">
			<Skeleton class="mt-0.5 size-4 shrink-0 rounded-4" />
			<div class="flex-1 space-y-1.5">
				<Skeleton class="h-4 w-1/2 rounded-4" />
				<Skeleton class="h-3 w-3/4 rounded-4" />
			</div>
		</div>
	</div>
</template>
