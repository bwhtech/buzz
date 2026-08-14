<script setup lang="ts">
// A setting shown as a card: what it controls, and where it currently stands. The whole
// card is the button, so the status is as clickable as the label.
defineProps<{ icon: string; label: string; status: string }>();
</script>

<template>
	<button
		type="button"
		class="flex w-full items-center gap-3 rounded-xl border border-outline-gray-2 bg-surface-white p-3 text-left transition-colors hover:border-outline-gray-3"
	>
		<span
			class="grid size-10 shrink-0 place-items-center rounded-lg bg-surface-gray-2"
			aria-hidden="true"
		>
			<span :class="icon" class="size-5 text-ink-gray-7" />
		</span>

		<span class="min-w-0">
			<span class="block truncate text-base font-medium text-ink-gray-9">{{ label }}</span>
			<span class="block truncate text-sm text-ink-gray-5">{{ status }}</span>
		</span>
	</button>
</template>
