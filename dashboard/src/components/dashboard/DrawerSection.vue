<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>

<template>
	<section class="space-y-3 border-t border-outline-gray-1 pt-4 first:border-t-0 first:pt-0">
		<div>
			<h3 class="text-base font-semibold text-ink-gray-9">{{ title }}</h3>
			<p v-if="description" class="mt-0.5 text-sm text-ink-gray-5">{{ description }}</p>
		</div>
		<div class="space-y-4">
			<slot />
		</div>
	</section>
</template>
