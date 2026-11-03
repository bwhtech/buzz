<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>

<template>
	<section class="flex scroll-mt-7 flex-col gap-2">
		<div class="px-1">
			<h2 class="text-p-base font-medium text-ink-gray-6">{{ title }}</h2>
			<p v-if="description" class="mt-0.5 text-p-sm text-ink-gray-5">{{ description }}</p>
		</div>
		<div
			class="divide-y divide-outline-gray-1 rounded-5 bg-surface-base ring-1 ring-inset ring-outline-gray-2"
		>
			<slot />
		</div>
	</section>
</template>
