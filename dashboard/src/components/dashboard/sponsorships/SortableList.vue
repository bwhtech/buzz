<script setup lang="ts" generic="Item">
import { Button } from "frappe-ui"
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
		isLocked?: (item: Item) => boolean
	}>(),
	{ minRows: 0, isLocked: () => false },
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
		<ul ref="listElement" class="space-y-2">
			<li
				v-for="(item, index) in items"
				:key="index"
				class="group flex items-center gap-1 rounded-4 transition-opacity"
				:class="{ 'opacity-40': draggedIndex === index }"
				@dragover.prevent
				@drop="dropAt(index)"
			>
				<Button
					variant="ghost"
					icon="lucide-grip-vertical"
					class="cursor-grab disabled:invisible"
					:draggable="!disabled"
					:disabled="disabled"
					:label="`Reorder ${itemName} ${index + 1}`"
					@dragstart="draggedIndex = index"
					@dragend="draggedIndex = null"
					@keydown="moveWithArrowKeys($event, index)"
				/>
				<slot name="row" :item="item" :index="index" :add="addItem" />
				<Button
					v-if="!disabled && items.length > minRows && !isLocked(item)"
					variant="ghost"
					icon="lucide-x"
					:label="`Remove ${itemName} ${index + 1}`"
					@click="removeItem(index)"
				/>
				<!-- Holds the remove button's width so every row's fields line up. -->
				<span v-else-if="!disabled" class="size-7 shrink-0" aria-hidden="true" />
			</li>
		</ul>
		<Button
			v-if="!disabled"
			variant="ghost"
			icon-left="lucide-plus"
			:label="addLabel"
			@click="addItem"
		/>
	</div>
</template>
