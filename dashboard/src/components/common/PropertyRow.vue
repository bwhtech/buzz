<script setup lang="ts">
// One row of a drawer's property list: an icon and label, then the value in the slot.
defineProps<{ label: string; icon: string }>()
</script>

<template>
	<div class="flex items-start gap-3 py-1.5">
		<dt class="flex w-32 shrink-0 items-start gap-2 text-base text-ink-gray-5">
			<span :class="icon" class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
			<span class="min-w-0 text-pretty [overflow-wrap:anywhere]">{{ label }}</span>
		</dt>
		<dd class="min-w-0 flex-1 text-base break-words text-ink-gray-8">
			<slot />
		</dd>
	</div>
</template>
