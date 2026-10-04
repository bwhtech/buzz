<script setup lang="ts">
import { Button } from "frappe-ui"

/** The bar a list shows while rows are selected: what is selected, and what can be done. */
defineProps<{ count: number; label: string }>()
defineEmits<{ clear: [] }>()
</script>

<template>
	<Transition name="bar">
		<!-- The sticky box carries no height of its own, so a selection floats the bar over the
		     rows at the top of the view instead of pushing the whole list down. -->
		<div v-if="count" class="sticky top-2 z-20 h-0">
			<div
				role="toolbar"
				:aria-label="__('Bulk actions')"
				class="mx-auto flex w-max max-w-full flex-wrap items-center justify-center gap-3 rounded-6 bg-surface-base px-4 py-2 shadow-2xl"
			>
				<span class="text-sm text-ink-gray-7">{{ label }}</span>

				<div class="flex items-center gap-2">
					<slot />

					<Button variant="ghost" :label="__('Clear selection')" @click="$emit('clear')">
						<template #icon>
							<span class="lucide-x size-4" />
						</template>
					</Button>
				</div>
			</div>
		</div>
	</Transition>
</template>

<style scoped>
/* Opacity alone: the bar stays pinned while the rows move, so it has nowhere to slide from. */
.bar-enter-active,
.bar-leave-active {
	transition: opacity 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

.bar-enter-from,
.bar-leave-to {
	opacity: 0;
}
</style>
