<script setup lang="ts">
defineProps<{ title: string; description?: string; stacked?: boolean }>()
</script>

<template>
	<div
		class="flex flex-col gap-2.5 border-b border-outline-gray-1 py-4 last:border-b-0"
		:class="{ 'sm:flex-row sm:items-center sm:justify-between sm:gap-6': !stacked }"
	>
		<div class="min-w-0">
			<div class="text-p-base font-medium text-ink-gray-8">{{ title }}</div>
			<div v-if="description" class="mt-1 text-p-sm text-ink-gray-5">{{ description }}</div>
		</div>
		<div class="shrink-0" :class="{ 'sm:w-[280px]': !stacked }">
			<slot />
		</div>
	</div>
</template>
