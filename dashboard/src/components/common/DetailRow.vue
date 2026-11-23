<script setup lang="ts">
// One line of a detail list: label on the left, value beside it, and an optional action
// at the end, usually an icon-only button. Both sides are slots, so a row can hold a
// badge or a link instead of plain text. `icon` leads the label in a wider column;
// `wrap` lets a long value wrap instead of truncating.
withDefaults(
	defineProps<{ label?: string; value?: string | null; icon?: string; wrap?: boolean }>(),
	{ label: "", value: null, icon: undefined, wrap: false },
)
</script>

<template>
	<div class="flex gap-3" :class="icon ? 'items-start' : 'items-baseline'">
		<dt class="flex shrink-0 items-start gap-2 text-ink-gray-5" :class="icon ? 'w-32' : 'w-24'">
			<span v-if="icon" :class="icon" class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
			<span class="min-w-0 text-pretty [overflow-wrap:anywhere]">
				<slot name="label">{{ label }}</slot>
			</span>
		</dt>
		<dd class="flex min-w-0 flex-1 items-baseline gap-2">
			<div class="min-w-0 flex-1 text-ink-gray-8" :class="wrap ? 'break-words' : 'truncate'">
				<slot>
					<span v-if="value">{{ value }}</span>
					<span v-else class="text-ink-gray-5">—</span>
				</slot>
			</div>
			<slot name="suffix" />
		</dd>
	</div>
</template>
