<script setup lang="ts">
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"

// A record's id as `#ID` that copies itself; `label` names it in the toast, e.g. "Ticket ID".
const props = defineProps<{ value: string; label: string }>()

const copy = useCopyToClipboard()
</script>

<template>
	<button
		type="button"
		class="copy-id cursor-copy font-mono text-sm tracking-wider text-ink-gray-5 uppercase hover:text-ink-gray-7"
		:aria-label="`Copy ${props.label} ${value}`"
		@click="copy(value, `${props.label} copied`)"
	>
		#{{ value }}
	</button>
</template>

<style scoped>
.copy-id {
	--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
	transition:
		color 160ms var(--ease-out),
		transform 160ms var(--ease-out);
}

.copy-id:active {
	transform: scale(0.97);
}

@media (prefers-reduced-motion: reduce) {
	.copy-id:active {
		transform: none;
	}
}
</style>
