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

const { appliedTags, appliedNames, options, setTags, removeTag, createTag } = useDocumentTags(
	props,
	() => emit("changed"),
)

const open = ref(false)
const query = ref("")
const newTagLabel = ref<string | null>(null)
watch(open, (isOpen) => {
	query.value = ""
	if (!isOpen) newTagLabel.value = null
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
	condition: ({ query: searchText }: { query: string }) =>
		searchText.trim() !== "" &&
		!options.value.some((tag) => tag.label.toLowerCase() === searchText.trim().toLowerCase()),
	onClick: ({ query: searchText }: { query: string }) => (newTagLabel.value = searchText.trim()),
}

const comboboxOptions = computed(() => {
	if (newTagLabel.value !== null) return TAG_COLORS.map(colorOption)
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
			createTag(newTagLabel.value!, color)
			newTagLabel.value = null
		},
	}
}

function addSelectedTag(option: { value: string | number } | null) {
	const tag = options.value.find((each) => each.name === option?.value)
	if (tag) setTags([...appliedTags.value, tag])
}

// Escape or a click outside steps back out of the colour list before it closes the menu.
function setMenuOpen(isOpen: boolean) {
	if (!isOpen && newTagLabel.value !== null) return (newTagLabel.value = null)
	open.value = isOpen
}

// Combobox highlights the first colour; arrow down to the suggested one, as a user would.
watch(newTagLabel, async (label) => {
	query.value = ""
	if (label === null) return
	await nextTick()
	const steps = TAG_COLORS.indexOf(suggestedColor.value)
	requestAnimationFrame(() => {
		const searchInput = document.activeElement
		if (searchInput?.getAttribute("role") !== "combobox") return
		for (let step = 0; step < steps; step++)
			searchInput.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }))
	})
})
</script>

<template>
	<div class="flex flex-wrap items-center gap-1.5" aria-label="Tags" role="group">
		<TagBadge v-for="tag in appliedTags" :key="tag.name" :color="tag.color" :label="tag.label">
			<template v-if="!disabled" #suffix>
				<button
					type="button"
					class="-m-1 grid place-items-center rounded-full p-1 opacity-60 outline-none transition-opacity duration-150 hover:opacity-100 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-outline-gray-3"
					:aria-label="`Remove ${tag.label}`"
					@click="removeTag(tag)"
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
			:placeholder="newTagLabel === null ? 'Search or create tag' : 'Pick a color'"
			empty-text="Type a name to create a tag"
			@update:open="setMenuOpen"
			@update:selected-option="addSelectedTag"
		>
			<template #trigger>
				<button
					type="button"
					class="flex h-5 items-center gap-1 rounded-full border border-dashed border-outline-gray-3 px-2 text-xs text-ink-gray-5 transition-[transform,color,border-color] duration-150 ease-out hover:border-outline-gray-4 hover:text-ink-gray-7 active:scale-[0.97] motion-reduce:transform-none"
					aria-label="Add tag"
				>
					<span class="lucide-plus size-3" aria-hidden="true" />
					<span v-if="!appliedTags.length">Add tag</span>
				</button>
			</template>

			<template v-if="newTagLabel !== null" #search-prefix>
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-chevron-left"
					aria-label="Back"
					class="-ml-2"
					@click="newTagLabel = null"
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
			<template #item-label="{ item, query: searchText }">
				<span class="block truncate">
					{{ item.key === "create" ? `Create “${searchText.trim()}”` : item.label }}
				</span>
			</template>
		</Combobox>
	</div>
</template>
