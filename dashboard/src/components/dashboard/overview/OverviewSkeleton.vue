<script setup lang="ts">
import { Skeleton } from "frappe-ui"

// Shaped like the hero and the setup cards, so the content settles into the boxes.
defineProps<{ part: "hero" | "steps" }>()
</script>

<template>
	<section
		v-if="part === 'hero'"
		class="flex gap-5 rounded-5 border border-outline-gray-2 p-3 max-sm:flex-col"
	>
		<Skeleton class="aspect-[1.91/1] w-full shrink-0 rounded-4 sm:w-[280px]" />
		<div class="flex flex-1 flex-col gap-4 py-1">
			<Skeleton class="h-5 w-12 rounded-4" />
			<Skeleton class="h-7 w-2/3 rounded-4" />
			<Skeleton class="h-10 w-1/2 rounded-4" />
			<Skeleton class="h-10 w-1/2 rounded-4" />
		</div>
	</section>
	<section v-else class="space-y-4">
		<Skeleton class="h-7 w-40 rounded-4" />
		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			<Skeleton v-for="card in 3" :key="card" class="h-56 rounded-6" />
		</div>
	</section>
</template>
