<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>

<template>
	<!-- On a phone each section is a card under a small grey label. -->
	<section class="flex scroll-mt-7 flex-col">
		<h2
			class="mb-1 px-1 text-p-sm font-medium text-ink-gray-5 md:px-0 md:text-[16px] md:font-semibold md:text-ink-gray-9"
		>
			{{ title }}
		</h2>
		<p v-if="description" class="px-1 text-p-sm text-ink-gray-5 md:px-0">{{ description }}</p>
		<div
			class="max-md:mt-1.5 max-md:rounded-5 max-md:px-3.5 max-md:py-1 max-md:ring-1 max-md:ring-inset max-md:ring-outline-gray-2"
		>
			<slot />
		</div>
	</section>
</template>
