<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
	<section class="space-y-3">
		<h3 class="text-lg font-semibold text-ink-gray-9">{{ title }}</h3>
		<slot />
	</section>
</template>
