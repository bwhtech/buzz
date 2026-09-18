<script setup lang="ts">
defineProps<{
	title: string
	description?: string
}>()
</script>

<template>
	<div class="flex flex-col items-center gap-2 py-12 text-center">
		<div v-if="$slots.illustration" class="mb-1 flex rounded-4 bg-surface-gray-2 p-2">
			<slot name="illustration" />
		</div>

		<h2 class="text-lg-medium text-ink-gray-8">{{ title }}</h2>
		<p v-if="description" class="text-base text-ink-gray-5">{{ description }}</p>
	</div>
</template>
