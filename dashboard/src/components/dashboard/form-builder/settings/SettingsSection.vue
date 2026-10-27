<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>

<template>
	<section class="flex scroll-mt-7 flex-col">
		<h2 class="mb-1 text-[16px] font-semibold text-ink-gray-9">{{ title }}</h2>
		<p v-if="description" class="text-p-sm text-ink-gray-5">{{ description }}</p>
		<slot />
	</section>
</template>
