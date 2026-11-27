<script setup lang="ts">
import { CollapsibleContent, CollapsibleRoot, CollapsibleTrigger } from "reka-ui"

import type { GuestAnswer } from "@/types"

defineProps<{ answers: GuestAnswer[] }>()
</script>

<template>
	<CollapsibleRoot
		v-slot="{ open }"
		as="section"
		class="overflow-hidden rounded-5 border border-outline-gray-2"
	>
		<CollapsibleTrigger
			class="answers-trigger flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-surface-gray-1 focus-visible:focus-ring"
		>
			<span
				class="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6"
				aria-hidden="true"
			>
				<span class="lucide-clipboard-list size-4" />
			</span>
			<span class="min-w-0 flex-1">
				<span class="block text-base font-medium text-ink-gray-9">Registration answers</span>
				<span class="block text-sm text-ink-gray-5">
					{{ answers.length }} {{ answers.length === 1 ? "answer" : "answers" }} ·
					{{ open ? "Hide" : "Show" }}
				</span>
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

		<CollapsibleContent class="answers-content">
			<dl class="divide-y divide-outline-gray-1 border-t border-outline-gray-2 px-4">
				<div v-for="answer in answers" :key="answer.label" class="space-y-1 py-3">
					<dt class="text-sm text-pretty text-ink-gray-5">{{ answer.label }}</dt>
					<dd class="text-base whitespace-pre-line [overflow-wrap:anywhere] text-ink-gray-8">
						{{ answer.value }}
					</dd>
				</div>
			</dl>
		</CollapsibleContent>
	</CollapsibleRoot>
</template>

<style scoped>
.answers-trigger {
	transition: background-color 150ms ease;
}

/* reka measures the panel and exposes its height; without it the answers snap open. */
.answers-content {
	overflow: hidden;
}
.answers-content[data-state="open"] {
	animation: answers-open 220ms cubic-bezier(0.23, 1, 0.32, 1);
}
.answers-content[data-state="closed"] {
	animation: answers-close 160ms cubic-bezier(0.23, 1, 0.32, 1);
}

@keyframes answers-open {
	from {
		height: 0;
	}
	to {
		height: var(--reka-collapsible-content-height);
	}
}
@keyframes answers-close {
	from {
		height: var(--reka-collapsible-content-height);
	}
	to {
		height: 0;
	}
}

@media (prefers-reduced-motion: reduce) {
	.answers-content[data-state] {
		animation: none;
	}
}
</style>
