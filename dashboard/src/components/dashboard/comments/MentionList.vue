<script setup lang="ts">
import { Avatar, ItemListRow } from "frappe-ui"
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
		class="mention-list w-64 rounded-5 bg-surface-elevation-3 p-1 shadow-xl ring-1 ring-outline-gray-1"
		role="listbox"
		aria-label="Team members"
	>
		<ItemListRow
			v-for="(item, index) in items"
			:key="item.id"
			role="option"
			:active="index === active"
			:aria-selected="index === active"
			class="cursor-pointer"
			@mousedown.prevent="pick(index)"
			@mousemove="active = index"
		>
			<template #prefix>
				<Avatar size="sm" :label="item.label" :image="item.image ?? undefined" />
			</template>
			<template #label>{{ item.label }}</template>
			<template #suffix>
				<span class="text-xs text-ink-gray-5">{{ item.role }}</span>
			</template>
		</ItemListRow>
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
