<script setup lang="ts">
import { Button, TextInput } from "frappe-ui"
import { nextTick, ref, watch } from "vue"

const text = defineModel<string | null | undefined>({ required: true })

const split = (value?: string | null) => (value ? value.split("\n") : [])
const joined = (list: string[]) => list.filter((option) => option.trim()).join("\n")

// Blank rows stay on screen while being typed into, but never reach the saved options.
const options = ref<string[]>(split(text.value))
watch(options, (list) => (text.value = joined(list)), { deep: true })
watch(text, (value) => value !== joined(options.value) && (options.value = split(value)))

const list = ref<HTMLElement | null>(null)
const focusAt = (index: number) =>
	nextTick().then(() => list.value?.querySelectorAll("input")[index]?.focus())

function add(at = options.value.length) {
	options.value.splice(at, 0, "")
	focusAt(at)
}

function removeIfEmpty(index: number, keydown: KeyboardEvent) {
	if (options.value[index]) return
	keydown.preventDefault()
	options.value.splice(index, 1)
	focusAt(Math.max(index - 1, 0))
}

const dragged = ref<number | null>(null)

// Reordered while dragging, so the list moves under the pointer.
function dragOver(index: number) {
	if (dragged.value === null || dragged.value === index) return
	const [option] = options.value.splice(dragged.value, 1)
	options.value.splice(index, 0, option)
	dragged.value = index
}
</script>

<template>
	<div class="flex flex-col gap-1.5">
		<span class="text-xs text-ink-gray-5">Options</span>
		<ul ref="list" class="flex flex-col gap-1.5">
			<li
				v-for="(option, index) in options"
				:key="index"
				class="flex items-center gap-1"
				:class="{ 'opacity-50': dragged === index }"
				@dragover.prevent="dragOver(index)"
			>
				<span
					draggable="true"
					class="grid h-7 w-4 shrink-0 cursor-grab place-items-center text-ink-gray-5 active:cursor-grabbing"
					aria-hidden="true"
					@dragstart="dragged = index"
					@dragend="dragged = null"
				>
					<span class="lucide-grip-vertical size-4" />
				</span>
				<TextInput
					v-model="options[index]"
					class="flex-1"
					:aria-label="`Option ${index + 1}`"
					@keydown.enter.prevent="add(index + 1)"
					@keydown.backspace="removeIfEmpty(index, $event)"
				/>
				<Button
					variant="ghost"
					icon="lucide-x"
					:label="`Remove option ${index + 1}`"
					@click="options.splice(index, 1)"
				/>
			</li>
		</ul>
		<Button
			class="self-start"
			variant="ghost"
			icon-left="lucide-plus"
			label="Add option"
			@click="add()"
		/>
	</div>
</template>
