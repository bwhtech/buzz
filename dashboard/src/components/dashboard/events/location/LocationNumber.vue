<script setup lang="ts">
defineProps<{ number: number }>()
</script>

<template>
	<span
		class="grid size-5 shrink-0 place-items-center rounded-full bg-[--ink-gray-9] text-xs font-semibold tabular-nums text-[--surface-base]"
	>
		{{ number }}
	</span>
</template>
