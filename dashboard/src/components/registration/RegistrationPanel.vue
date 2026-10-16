<template>
	<section class="overflow-hidden rounded-[14px] border border-outline-gray-2 md:rounded-7">
		<header class="flex flex-col gap-0.5 border-b border-outline-gray-1 px-4 py-3">
			<h2 class="text-base font-semibold text-ink-gray-9">{{ title }}</h2>
			<p v-if="description" class="text-p-sm text-ink-gray-5">{{ description }}</p>
		</header>
		<div class="p-4">
			<slot />
		</div>
	</section>
</template>

<script setup lang="ts">
defineProps<{ title: string; description?: string }>()
</script>
