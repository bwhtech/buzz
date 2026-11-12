<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
	<section class="space-y-3">
		<h3 class="text-base font-semibold text-ink-gray-8">{{ title }}</h3>
		<slot />
	</section>
</template>
