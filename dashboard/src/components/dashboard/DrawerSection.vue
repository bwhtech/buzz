<script setup lang="ts">
defineProps<{ title: string }>()
</script>

<template>
	<section class="space-y-3 border-t border-outline-gray-1 pt-4">
		<h3 class="text-base font-semibold text-ink-gray-9">{{ title }}</h3>
		<div class="space-y-4">
			<slot />
		</div>
	</section>
</template>
