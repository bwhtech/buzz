<script setup lang="ts">
// One line of a detail list: label on the left, value beside it, and an optional action
// at the end — usually an icon-only button. Both sides are slots, so a row can hold a
// badge or a link instead of plain text.
withDefaults(defineProps<{ label?: string; value?: string | null }>(), { label: "", value: null })
</script>

<template>
	<div class="flex items-baseline gap-3">
		<dt class="w-24 shrink-0 text-ink-gray-5">
			<slot name="label">{{ label }}</slot>
		</dt>
		<dd class="flex min-w-0 flex-1 items-baseline gap-2">
			<div class="min-w-0 flex-1 truncate text-ink-gray-8">
				<slot>
					<span v-if="value">{{ value }}</span>
					<span v-else class="text-ink-gray-5">—</span>
				</slot>
			</div>
			<slot name="suffix" />
		</dd>
	</div>
</template>
