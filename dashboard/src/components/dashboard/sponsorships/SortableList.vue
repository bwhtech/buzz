<script setup lang="ts" generic="Item">
import { nextTick, ref } from "vue"

const items = defineModel<Item[]>({ required: true })
const props = withDefaults(
	defineProps<{
		label: string
		addLabel: string
		itemName: string
		createItem: () => Item
		minRows?: number
		disabled?: boolean
	}>(),
	{ minRows: 0 },
)
defineSlots<{ row(props: { item: Item; index: number; add: () => void }): unknown }>()

const listElement = ref<HTMLUListElement>()
const draggedIndex = ref<number | null>(null)

function moveItem(fromIndex: number, toIndex: number) {
	if (toIndex < 0 || toIndex >= items.value.length || fromIndex === toIndex) return
	const reorderedItems = [...items.value]
	reorderedItems.splice(toIndex, 0, ...reorderedItems.splice(fromIndex, 1))
	items.value = reorderedItems
}

function dropAt(toIndex: number) {
	if (draggedIndex.value !== null) moveItem(draggedIndex.value, toIndex)
	draggedIndex.value = null
}

function removeItem(index: number) {
	items.value = items.value.filter((_, itemIndex) => itemIndex !== index)
}

async function addItem() {
	items.value = [...items.value, props.createItem()]
	await nextTick()
	listElement.value?.querySelector<HTMLElement>("li:last-child :is(input, select)")?.focus()
}

// Arrow keys on the handle reorder too, so the list works without a pointer.
async function moveWithArrowKeys(event: KeyboardEvent, index: number) {
	const offset = { ArrowUp: -1, ArrowDown: 1 }[event.key]
	if (!offset) return
	event.preventDefault()
	moveItem(index, index + offset)
	await nextTick()
	listElement.value?.children[index + offset]?.querySelector("button")?.focus()
}
</script>

<template>
	<div class="space-y-1.5">
		<span class="block text-xs text-ink-gray-5">{{ label }}</span>
		<ul ref="listElement" class="space-y-0.5">
			<li
				v-for="(item, index) in items"
				:key="index"
				class="group flex items-center gap-1 rounded-4 transition-opacity"
				:class="{ 'opacity-40': draggedIndex === index }"
				@dragover.prevent
				@drop="dropAt(index)"
			>
				<button
					type="button"
					class="flex size-7 shrink-0 cursor-grab items-center justify-center rounded-4 text-ink-gray-4 hover:text-ink-gray-7 focus-visible:outline-none focus-visible:focus-ring disabled:cursor-default disabled:opacity-0"
					:draggable="!disabled"
					:disabled="disabled"
					:aria-label="`Reorder ${itemName} ${index + 1}`"
					@dragstart="draggedIndex = index"
					@dragend="draggedIndex = null"
					@keydown="moveWithArrowKeys($event, index)"
				>
					<span class="lucide-grip-vertical size-4" aria-hidden="true" />
				</button>
				<slot name="row" :item="item" :index="index" :add="addItem" />
				<button
					v-if="!disabled && items.length > minRows"
					type="button"
					class="flex size-7 shrink-0 items-center justify-center rounded-4 text-ink-gray-4 transition-opacity hover:text-ink-gray-7 focus-visible:opacity-100 focus-visible:outline-none focus-visible:focus-ring group-hover:opacity-100 [@media(hover:hover)]:opacity-0"
					:aria-label="`Remove ${itemName} ${index + 1}`"
					@click="removeItem(index)"
				>
					<span class="lucide-x size-4" aria-hidden="true" />
				</button>
			</li>
		</ul>
		<button
			v-if="!disabled"
			type="button"
			class="flex items-center gap-1 rounded-4 py-1 text-base text-ink-gray-5 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:focus-ring"
			@click="addItem"
		>
			<span class="flex size-7 items-center justify-center">
				<span class="lucide-plus size-4" aria-hidden="true" />
			</span>
			{{ addLabel }}
		</button>
	</div>
</template>
