<script setup lang="ts">
defineProps<{
	title: string
	description?: string
}>()
</script>

<template>
	<div class="flex flex-col items-center gap-2 py-12 text-center">
		<slot name="illustration" />

		<h2 class="text-lg-medium text-ink-gray-8">{{ title }}</h2>
		<p v-if="description" class="text-base text-ink-gray-5">{{ description }}</p>
	</div>
</template>
