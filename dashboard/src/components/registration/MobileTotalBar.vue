<template>
	<div
		class="fixed inset-x-0 bottom-0 z-20 flex flex-col gap-3 border-t border-outline-gray-2 bg-surface-base px-4 pb-[max(16px,env(safe-area-inset-bottom))] pt-3"
	>
		<slot name="notice" />
		<div class="flex items-center gap-3">
			<button
				type="button"
				class="flex min-h-11 min-w-0 flex-1 flex-col justify-center text-left transition-transform duration-150 ease-out active:scale-[0.97]"
				:aria-label="__('Show order summary')"
				@click="emit('open-summary')"
			>
				<span class="flex items-center gap-1 text-xs text-ink-gray-5">
					{{ countLabel }}
					<LucideChevronUp class="size-3" />
				</span>
				<span class="flex items-baseline gap-1.5">
					<span class="text-lg font-semibold tabular-nums text-ink-gray-9">{{ total }}</span>
					<span v-if="before" class="text-xs text-ink-gray-5 line-through">{{ before }}</span>
				</span>
			</button>
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
import LucideChevronUp from "~icons/lucide/chevron-up"

defineProps<{ countLabel: string; total: string; before?: string }>()
const emit = defineEmits<{ "open-summary": [] }>()
</script>
