<script setup lang="ts">
import { useClipboard } from "@vueuse/core"
import { computed } from "vue"

// The event link, ready to share: the address beside a copy button.
const props = defineProps<{ route: string }>()

const url = computed(() => `${window.location.origin}/${props.route}`)
const display = computed(() => url.value.replace(/^https?:\/\//, ""))
const { copy: copyText, copied } = useClipboard({ legacy: true, copiedDuring: 1600 })
const copy = () => copyText(url.value)
</script>

<template>
	<div class="flex h-7 min-w-0 items-center gap-1 rounded-4 bg-surface-gray-2 pl-2.5 pr-0.5">
		<span class="lucide-link size-3.5 shrink-0 text-ink-gray-5" aria-hidden="true" />
		<span class="min-w-0 flex-1 truncate text-p-sm text-ink-gray-6">{{ display }}</span>
		<button
			type="button"
			class="copy-button grid h-6 shrink-0 place-items-center rounded-3 px-2 text-p-sm font-medium text-ink-gray-8"
			:data-copied="copied || undefined"
			@click="copy"
		>
			<span class="copy-label col-start-1 row-start-1">Copy</span>
			<span class="copy-done col-start-1 row-start-1 text-ink-green-6">Copied</span>
		</button>
	</div>
</template>

<style scoped>
/* The label swaps through a short blur, so it reads as one control changing state. */
.copy-button {
	transition:
		background-color 150ms ease,
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}
.copy-button:active {
	transform: scale(0.96);
}
@media (hover: hover) and (pointer: fine) {
	.copy-button:hover {
		background: var(--surface-gray-3);
	}
}
.copy-label,
.copy-done {
	transition:
		opacity 200ms ease,
		filter 200ms ease,
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.copy-done,
[data-copied] .copy-label {
	opacity: 0;
	filter: blur(2px);
	transform: scale(0.9);
}
[data-copied] .copy-done {
	opacity: 1;
	filter: none;
	transform: none;
}
</style>
