<script setup lang="ts">
// The places picked for a venue with several locations, in the order attendees see them.
import { Button } from "frappe-ui"
import { computed, nextTick, ref, useTemplateRef } from "vue"

import LocationNumber from "@/components/dashboard/events/location/LocationNumber.vue"
import type { Venue } from "@/data/venues"

const props = defineProps<{ places: Venue[]; hovered: string | null; isSaving: boolean }>()
const selected = defineModel<string[]>({ required: true })
const emit = defineEmits<{ hover: [venue: string | null]; use: [] }>()

const list = useTemplateRef<HTMLOListElement>("list")
const dragged = ref<string | null>(null)
const countLabel = computed(() =>
	props.places.length === 1 ? "1 location" : `${props.places.length} locations`,
)

function move(name: string, toIndex: number) {
	if (toIndex < 0 || toIndex >= selected.value.length) return
	const reordered = selected.value.filter((venue) => venue !== name)
	reordered.splice(toIndex, 0, name)
	selected.value = reordered
}

// Reordered while dragging, so the pins renumber under the pointer.
function dragOver(index: number) {
	if (dragged.value) move(dragged.value, index)
}

// Arrow keys on the handle reorder too, so the list works without a pointer.
function moveWithArrowKeys(event: KeyboardEvent, name: string, index: number) {
	const offset = { ArrowUp: -1, ArrowDown: 1 }[event.key]
	if (!offset) return
	event.preventDefault()
	move(name, index + offset)
	nextTick().then(() => list.value?.children[index + offset]?.querySelector("button")?.focus())
}

function remove(name: string) {
	selected.value = selected.value.filter((venue) => venue !== name)
	emit("hover", null)
}

// The street and the city: enough to tell two places apart without the full address.
function areaOf(place: Venue) {
	const parts = place.address?.split(", ") ?? []
	return parts.length > 4 ? parts.slice(-4, -2).join(", ") : place.address
}
</script>

<template>
	<div class="flex flex-col overflow-hidden">
		<div class="flex items-baseline justify-between px-3.5 pb-1.5 pt-3">
			<p class="text-base font-semibold text-ink-gray-9">{{ countLabel }}</p>
			<p v-if="places.length > 1" class="text-sm text-ink-gray-5">Drag to reorder</p>
		</div>
		<ol ref="list" class="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-1.5">
			<li
				v-for="(place, index) in places"
				:key="place.name"
				class="flex min-h-11 items-center gap-2 rounded-4 pl-0.5 pr-1 transition-[background-color,opacity] duration-100"
				:class="[
					dragged === place.name && 'opacity-50',
					(hovered === place.name || dragged === place.name) && 'bg-surface-gray-2',
				]"
				@dragover.prevent="dragOver(index)"
				@pointerenter="!dragged && $emit('hover', place.name)"
				@pointerleave="$emit('hover', null)"
			>
				<button
					type="button"
					class="flex size-6 shrink-0 cursor-grab items-center justify-center rounded-4 text-ink-gray-4 hover:text-ink-gray-7 focus-visible:outline-none focus-visible:focus-ring"
					draggable="true"
					:aria-label="`Reorder ${place.venue_name}`"
					@dragstart="dragged = place.name"
					@dragend="dragged = null"
					@keydown="moveWithArrowKeys($event, place.name, index)"
				>
					<span class="lucide-grip-vertical size-3.5" aria-hidden="true" />
				</button>
				<LocationNumber :number="index + 1" />
				<div class="min-w-0 flex-1">
					<p class="truncate text-base text-ink-gray-8">{{ place.venue_name }}</p>
					<p v-if="areaOf(place)" class="truncate text-sm text-ink-gray-5">{{ areaOf(place) }}</p>
				</div>
				<Button
					size="sm"
					variant="ghost"
					icon="lucide-x"
					:aria-label="`Remove ${place.venue_name}`"
					@click="remove(place.name)"
				/>
			</li>
		</ol>
		<div class="p-3 pt-2.5">
			<Button
				class="w-full"
				variant="solid"
				:label="places.length < 2 ? 'Pick at least 2 locations' : `Use ${places.length} locations`"
				:disabled="places.length < 2"
				:loading="isSaving"
				@click="$emit('use')"
			/>
		</div>
	</div>
</template>
