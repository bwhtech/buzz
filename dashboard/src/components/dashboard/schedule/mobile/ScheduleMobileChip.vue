<script setup lang="ts">
defineProps<{ active?: boolean; size?: "md" | "lg" }>()
</script>

<template>
	<button
		type="button"
		class="flex shrink-0 select-none items-center gap-1.5 whitespace-nowrap rounded-full px-3 text-p-sm transition-colors duration-150 active:scale-[0.98]"
		:class="[
			size === 'lg' ? 'h-8' : 'h-[30px]',
			active ? 'bg-surface-gray-9 font-medium text-ink-base' : 'bg-surface-gray-2 text-ink-gray-7',
		]"
		:aria-pressed="active"
	>
		<span class="min-w-0 max-w-[200px] truncate"><slot /></span>
		<span
			v-if="$slots.count"
			class="tabular-nums"
			:class="active ? 'opacity-60' : 'text-ink-gray-5'"
			><slot name="count"
		/></span>
	</button>
</template>
