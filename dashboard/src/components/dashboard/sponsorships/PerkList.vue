<script setup lang="ts">
import { nextTick, ref } from "vue"

const perks = defineModel<string[]>({ required: true })
defineProps<{ disabled?: boolean }>()

const listElement = ref<HTMLUListElement>()
const draggedIndex = ref<number | null>(null)

function movePerk(fromIndex: number, toIndex: number) {
	if (toIndex < 0 || toIndex >= perks.value.length || fromIndex === toIndex) return
	const reorderedPerks = [...perks.value]
	reorderedPerks.splice(toIndex, 0, ...reorderedPerks.splice(fromIndex, 1))
	perks.value = reorderedPerks
}

function dropAt(toIndex: number) {
	if (draggedIndex.value !== null) movePerk(draggedIndex.value, toIndex)
	draggedIndex.value = null
}

function updatePerk(index: number, value: string) {
	perks.value = perks.value.map((perk, perkIndex) => (perkIndex === index ? value : perk))
}

function removePerk(index: number) {
	perks.value = perks.value.filter((_, perkIndex) => perkIndex !== index)
}

async function addPerk() {
	perks.value = [...perks.value, ""]
	await nextTick()
	listElement.value?.querySelector<HTMLInputElement>("li:last-child input")?.focus()
}

// Arrow keys on the handle reorder too, so the list works without a pointer.
async function moveWithArrowKeys(event: KeyboardEvent, index: number) {
	const offset = { ArrowUp: -1, ArrowDown: 1 }[event.key]
	if (!offset) return
	event.preventDefault()
	movePerk(index, index + offset)
	await nextTick()
	listElement.value?.children[index + offset]?.querySelector("button")?.focus()
}
</script>

<template>
	<div class="space-y-1.5">
		<span class="block text-xs text-ink-gray-5">Perks</span>
		<ul ref="listElement" class="space-y-0.5">
			<li
				v-for="(perk, index) in perks"
				:key="index"
				class="group flex items-center gap-1 rounded-4 transition-opacity"
				:class="{ 'opacity-40': draggedIndex === index }"
				@dragover.prevent
				@drop="dropAt(index)"
			>
				<button
					type="button"
					class="flex size-7 shrink-0 cursor-grab items-center justify-center rounded-4 text-ink-gray-4 hover:text-ink-gray-7 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 disabled:cursor-default disabled:opacity-0"
					:draggable="!disabled"
					:disabled="disabled"
					:aria-label="`Reorder ${perk || 'perk'}`"
					@dragstart="draggedIndex = index"
					@dragend="draggedIndex = null"
					@keydown="moveWithArrowKeys($event, index)"
				>
					<span class="lucide-grip-vertical size-4" aria-hidden="true" />
				</button>
				<input
					:value="perk"
					type="text"
					placeholder="Describe the perk"
					aria-label="Perk"
					:disabled="disabled"
					class="min-w-0 flex-1 border-0 bg-transparent px-1 py-1.5 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:outline-none focus:ring-0"
					@input="updatePerk(index, ($event.target as HTMLInputElement).value)"
					@keydown.enter.prevent="addPerk"
				/>
				<button
					v-if="!disabled"
					type="button"
					class="flex size-7 shrink-0 items-center justify-center rounded-4 text-ink-gray-4 opacity-0 transition-opacity hover:text-ink-gray-7 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3 group-hover:opacity-100"
					:aria-label="`Remove ${perk || 'perk'}`"
					@click="removePerk(index)"
				>
					<span class="lucide-x size-4" aria-hidden="true" />
				</button>
			</li>
		</ul>
		<button
			v-if="!disabled"
			type="button"
			class="flex items-center gap-1 rounded-4 py-1 text-base text-ink-gray-5 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
			@click="addPerk"
		>
			<span class="flex size-7 items-center justify-center">
				<span class="lucide-plus size-4" aria-hidden="true" />
			</span>
			Add perk
		</button>
	</div>
</template>
