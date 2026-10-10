<script setup lang="ts">
import { Button, Combobox } from "frappe-ui"
import { computed, nextTick, ref, watch } from "vue"

import TagBadge from "@/components/common/tags/TagBadge.vue"
import { TAG_COLORS, tagColorClasses } from "@/components/common/tags/tagColors"
import { useDocumentTags } from "@/composables/useDocumentTags"
import type { TagColor, TagItem } from "@/types"

// A record's tags as a chip row; each change applies at once, outside any save bar.
// Picking a tag adds it, so only unapplied tags are listed. "Create …" swaps in colours.
const props = defineProps<{
	team: string
	documentType: string
	documentName: string
	tags: TagItem[]
	options: TagItem[]
	disabled?: boolean
}>()
const emit = defineEmits<{ changed: [] }>()

const { applied, appliedNames, options, setTags, toggle, createTag } = useDocumentTags(props, () =>
	emit("changed"),
)

const open = ref(false)
const query = ref("")
const pendingLabel = ref<string | null>(null)
watch(open, (isOpen) => {
	query.value = ""
	if (!isOpen) pendingLabel.value = null
})

const suggestedColor = computed(() => {
	const used = new Set(options.value.map((tag) => tag.color))
	return TAG_COLORS.find((color) => color !== "gray" && !used.has(color)) ?? "blue"
})

const createOption = {
	type: "custom" as const,
	key: "create",
	label: "Create",
	keepOpen: true,
	condition: ({ query: typed }: { query: string }) =>
		typed.trim() !== "" &&
		!options.value.some((tag) => tag.label.toLowerCase() === typed.trim().toLowerCase()),
	onClick: ({ query: typed }: { query: string }) => (pendingLabel.value = typed.trim()),
}

const comboboxOptions = computed(() => {
	if (pendingLabel.value !== null) return TAG_COLORS.map(colorOption)
	const unapplied = options.value.filter((tag) => !appliedNames.value.includes(tag.name))
	return [
		...unapplied.map((tag) => ({ label: tag.label, value: tag.name, color: tag.color })),
		createOption,
	]
})

const capitalize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1)

// Custom options, like "Create …": their onClick fires on every pick, keyboard or mouse.
function colorOption(color: TagColor) {
	return {
		type: "custom" as const,
		key: color,
		label: capitalize(color),
		color,
		keepOpen: true,
		onClick: () => {
			createTag(pendingLabel.value!, color)
			pendingLabel.value = null
		},
	}
}

function onSelect(option: { value: string | number } | null) {
	const tag = options.value.find((each) => each.name === option?.value)
	if (tag) setTags([...applied.value, tag])
}

// Escape or a click outside steps back out of the colour list before it closes the menu.
function onOpenChange(isOpen: boolean) {
	if (!isOpen && pendingLabel.value !== null) return (pendingLabel.value = null)
	open.value = isOpen
}

// Combobox highlights the first colour; arrow down to the suggested one, as a user would.
watch(pendingLabel, async (label) => {
	query.value = ""
	if (label === null) return
	await nextTick()
	requestAnimationFrame(() => {
		for (let step = 0; step < TAG_COLORS.indexOf(suggestedColor.value); step++)
			document.activeElement?.dispatchEvent(
				new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
			)
	})
})
</script>

<template>
	<div class="flex flex-wrap items-center gap-1.5" aria-label="Tags" role="group">
		<TagBadge v-for="tag in applied" :key="tag.name" :color="tag.color" :label="tag.label">
			<template v-if="!disabled" #suffix>
				<button
					type="button"
					class="-m-1 grid place-items-center rounded-full p-1 opacity-60 outline-none transition-opacity duration-150 hover:opacity-100 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
					:aria-label="`Remove ${tag.label}`"
					@click="toggle(tag)"
				>
					<span class="lucide-x size-3" aria-hidden="true" />
				</button>
			</template>
		</TagBadge>

		<Combobox
			v-if="!disabled"
			v-model:query="query"
			trigger="button"
			:open="open"
			:options="comboboxOptions"
			:model-value="null"
			:placeholder="pendingLabel === null ? 'Search or create tag' : 'Pick a color'"
			empty-text="Type a name to create a tag"
			@update:open="onOpenChange"
			@update:selected-option="onSelect"
		>
			<template #trigger>
				<button
					type="button"
					class="flex h-5 items-center gap-1 rounded-full border border-dashed border-outline-gray-3 px-2 text-xs text-ink-gray-5 transition-[transform,color,border-color] duration-150 ease-out hover:border-outline-gray-4 hover:text-ink-gray-7 active:scale-[0.97] motion-reduce:transform-none"
					aria-label="Add tag"
				>
					<span class="lucide-plus size-3" aria-hidden="true" />
					<span v-if="!applied.length">Add tag</span>
				</button>
			</template>

			<template v-if="pendingLabel !== null" #search-prefix>
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-chevron-left"
					aria-label="Back"
					class="-ml-2"
					@click="pendingLabel = null"
				/>
			</template>

			<template #item-prefix="{ item }">
				<span
					v-if="item.color"
					class="size-2.5 rounded-full"
					:class="tagColorClasses(item.color).dot"
				/>
				<span v-else class="lucide-plus size-4 text-ink-gray-5" aria-hidden="true" />
			</template>
			<template #item-label="{ item, query: typed }">
				<span class="block truncate">
					{{ item.key === "create" ? `Create “${typed.trim()}”` : item.label }}
				</span>
			</template>
		</Combobox>
	</div>
</template>
