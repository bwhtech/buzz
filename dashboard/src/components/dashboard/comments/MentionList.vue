<script setup lang="ts">
import { Avatar } from "frappe-ui"
import { ref, watch } from "vue"

export interface MentionItem {
	id: string
	label: string
	image: string | null
	role: string
}

// Rendered by frappe-ui's suggestion renderer, which hands over tiptap's suggestion props.
const props = defineProps<{ items: MentionItem[]; command: (item: MentionItem) => void }>()

const active = ref(0)
watch(
	() => props.items,
	() => (active.value = 0),
)

function pick(index: number) {
	const item = props.items[index]
	if (item) props.command(item)
}

const MOVES: Record<string, number> = { ArrowDown: 1, ArrowUp: -1 }

function onKeyDown({ event }: { event: KeyboardEvent }): boolean {
	if (!props.items.length) return false
	if (event.key in MOVES) {
		active.value = (active.value + MOVES[event.key] + props.items.length) % props.items.length
		return true
	}
	if (event.key === "Enter" || event.key === "Tab") {
		pick(active.value)
		return true
	}
	return false
}

defineExpose({ onKeyDown })
</script>

<template>
	<div
		v-if="items.length"
		class="mention-list w-64 rounded-8 bg-surface-elevation-3 p-1 shadow-xl ring-1 ring-outline-gray-1"
		role="listbox"
		aria-label="Team members"
	>
		<button
			v-for="(item, index) in items"
			:key="item.id"
			type="button"
			role="option"
			:aria-selected="index === active"
			class="flex w-full items-center gap-2.5 rounded-6 px-2 py-1.5 text-left"
			:class="index === active && 'bg-surface-gray-2'"
			@mousedown.prevent="pick(index)"
			@mousemove="active = index"
		>
			<Avatar size="sm" :label="item.label" :image="item.image ?? undefined" />
			<span class="min-w-0 flex-1 truncate text-base text-ink-gray-8">{{ item.label }}</span>
			<span class="text-xs text-ink-gray-5">{{ item.role }}</span>
		</button>
	</div>
</template>

<style scoped>
.mention-list {
	transform-origin: bottom left;
	transition:
		opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

@starting-style {
	.mention-list {
		opacity: 0;
		transform: scale(0.97);
	}
}

@media (prefers-reduced-motion: reduce) {
	@starting-style {
		.mention-list {
			transform: none;
		}
	}
}
</style>
