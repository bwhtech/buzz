<script setup lang="ts">
import { CollapsibleContent, CollapsibleRoot, CollapsibleTrigger } from "reka-ui"

// A bordered card that folds its content away under an icon, a title and a summary
// line, e.g. "6 answers".
withDefaults(
	defineProps<{ icon: string; title: string; summary: string; defaultOpen?: boolean }>(),
	{
		defaultOpen: false,
	},
)
</script>

<template>
	<CollapsibleRoot
		v-slot="{ open }"
		:default-open="defaultOpen"
		as="section"
		class="overflow-hidden rounded-5 border border-outline-gray-2"
	>
		<CollapsibleTrigger
			class="card-trigger flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-gray-1 focus-visible:focus-ring focus-visible:outline-none"
		>
			<span
				class="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
				aria-hidden="true"
			>
				<span :class="icon" class="size-4" />
			</span>
			<span class="min-w-0 flex-1">
				<span class="block text-base font-medium text-ink-gray-9">{{ title }}</span>
				<span class="block text-sm text-ink-gray-5">{{ summary }}</span>
			</span>
			<span
				class="flex size-7 shrink-0 items-center justify-center rounded-full border border-outline-gray-2 bg-surface-white text-ink-gray-7"
				aria-hidden="true"
			>
				<span
					class="lucide-chevron-down size-4 transition-transform duration-200"
					:class="open && 'rotate-180'"
				/>
			</span>
		</CollapsibleTrigger>

		<CollapsibleContent class="card-content">
			<div class="border-t border-outline-gray-2">
				<slot />
			</div>
		</CollapsibleContent>
	</CollapsibleRoot>
</template>

<style scoped>
.card-trigger {
	transition: background-color 150ms ease;
}

/* reka measures the panel and exposes its height; without it the content snaps open. */
.card-content {
	overflow: hidden;
}
.card-content[data-state="open"] {
	animation: card-open 220ms cubic-bezier(0.23, 1, 0.32, 1);
}
.card-content[data-state="closed"] {
	animation: card-close 160ms cubic-bezier(0.23, 1, 0.32, 1);
}

@keyframes card-open {
	from {
		height: 0;
	}
	to {
		height: var(--reka-collapsible-content-height);
	}
}
@keyframes card-close {
	from {
		height: var(--reka-collapsible-content-height);
	}
	to {
		height: 0;
	}
}

@media (prefers-reduced-motion: reduce) {
	.card-content[data-state] {
		animation: none;
	}
}
</style>
