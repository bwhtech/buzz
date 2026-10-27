<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
	<section class="scroll-mt-8 rounded-8 bg-surface-base p-5 shadow-sm ring-1 ring-outline-gray-1">
		<h2 class="mb-4 text-p-base font-semibold text-ink-gray-9">{{ title }}</h2>
		<div class="space-y-4">
			<slot />
		</div>
	</section>
</template>
