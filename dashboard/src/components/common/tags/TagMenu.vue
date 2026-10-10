<script setup lang="ts">
import { Button, ItemListRow, TextInput } from "frappe-ui"
import { computed, nextTick, onMounted, ref, watch } from "vue"

import TagBadge from "@/components/common/tags/TagBadge.vue"
import { TAG_COLORS } from "@/components/common/tags/tagColors"
import type { TagColor, TagItem } from "@/types"

// Search a team's tags and toggle them, or name a new one and pick its colour in place.
const props = defineProps<{ options: TagItem[]; selected: string[] }>()
const emit = defineEmits<{ toggle: [tag: TagItem]; create: [label: string, color: TagColor] }>()

const query = ref("")
const pendingLabel = ref<string | null>(null)
const activeIndex = ref(0)
const activeColor = ref<TagColor | null>(null)
const searchInput = ref<InstanceType<typeof TextInput>>()
const colorList = ref<HTMLElement>()
const tagList = ref<HTMLElement>()

const label = computed(() => query.value.trim())
const matches = computed(() =>
	props.options.filter((tag) => tag.label.toLowerCase().includes(label.value.toLowerCase())),
)
const canCreate = computed(
	() =>
		label.value !== "" &&
		!props.options.some((tag) => tag.label.toLowerCase() === label.value.toLowerCase()),
)
const rowCount = computed(() => matches.value.length + (canCreate.value ? 1 : 0))

// The first colour no tag uses yet, so a run of new tags doesn't come out all the same.
const suggestedColor = computed(() => {
	const used = new Set(props.options.map((tag) => tag.color))
	return TAG_COLORS.find((color) => color !== "gray" && !used.has(color)) ?? "blue"
})

watch(query, () => (activeIndex.value = 0))
// The list scrolls, so arrowing past its edge would otherwise hide the row Enter picks.
watch(activeIndex, async (index) => {
	await nextTick()
	tagList.value?.querySelectorAll("[role=option]")[index]?.scrollIntoView({ block: "nearest" })
})
onMounted(focusSearch)

async function focusSearch() {
	await nextTick()
	searchInput.value?.focus()
}

function moveActive(step: number) {
	if (rowCount.value)
		activeIndex.value = (activeIndex.value + step + rowCount.value) % rowCount.value
}

function chooseActive() {
	const tag = matches.value[activeIndex.value]
	if (tag) pick(tag)
	else if (canCreate.value) startCreate()
}

function pick(tag: TagItem) {
	emit("toggle", tag)
	query.value = ""
	focusSearch()
}

async function startCreate() {
	pendingLabel.value = label.value
	await nextTick()
	colorList.value?.querySelector<HTMLElement>(`[data-color="${suggestedColor.value}"]`)?.focus()
}

function finishCreate(color: TagColor) {
	emit("create", pendingLabel.value!, color)
	pendingLabel.value = null
	query.value = ""
	focusSearch()
}

function cancelCreate() {
	pendingLabel.value = null
	focusSearch()
}

function moveColorFocus(event: KeyboardEvent, step: number) {
	const buttons = [...(colorList.value?.querySelectorAll<HTMLElement>("[data-color]") ?? [])]
	const index = buttons.indexOf(event.target as HTMLElement)
	buttons[(index + step + buttons.length) % buttons.length]?.focus()
}
</script>

<template>
	<div class="w-60 text-base">
		<template v-if="pendingLabel === null">
			<TextInput
				ref="searchInput"
				v-model="query"
				variant="ghost"
				placeholder="Search or create tag"
				aria-label="Search or create tag"
				@keydown.down.prevent="moveActive(1)"
				@keydown.up.prevent="moveActive(-1)"
				@keydown.enter.prevent="chooseActive"
			>
				<template #prefix><span class="lucide-search size-4" aria-hidden="true" /></template>
			</TextInput>
			<ul
				ref="tagList"
				class="mt-1 max-h-64 overflow-y-auto border-t border-outline-gray-1 pt-1"
				role="listbox"
				aria-label="Tags"
			>
				<ItemListRow
					v-for="(tag, index) in matches"
					:key="tag.name"
					as="li"
					role="option"
					class="cursor-pointer"
					:aria-selected="selected.includes(tag.name)"
					:active="index === activeIndex"
					@mouseenter="activeIndex = index"
					@click="pick(tag)"
				>
					<TagBadge :color="tag.color" :label="tag.label" />
					<template v-if="selected.includes(tag.name)" #suffix>
						<span class="lucide-check size-4 text-ink-gray-7" aria-hidden="true" />
					</template>
				</ItemListRow>
				<ItemListRow
					v-if="canCreate"
					as="li"
					role="option"
					class="cursor-pointer"
					:aria-selected="false"
					:active="activeIndex === matches.length"
					@mouseenter="activeIndex = matches.length"
					@click="startCreate"
				>
					<template #prefix>
						<span class="lucide-plus size-4 text-ink-gray-5" aria-hidden="true" />
					</template>
					<span class="block truncate">Create “{{ label }}”</span>
				</ItemListRow>
				<li v-if="!rowCount" class="px-2 py-3 text-center text-sm text-ink-gray-5">
					{{ options.length ? "No matching tags" : "Type a name to create a tag" }}
				</li>
			</ul>
		</template>

		<div v-else ref="colorList" @keydown.esc.stop.prevent="cancelCreate">
			<div class="flex items-center gap-1 border-b border-outline-gray-1 pb-1">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-chevron-left"
					aria-label="Back"
					@click="cancelCreate"
				/>
				<span class="truncate text-sm text-ink-gray-5">Pick a color</span>
			</div>
			<div class="mt-1 max-h-72 overflow-y-auto" role="listbox" aria-label="Tag color">
				<ItemListRow
					v-for="color in TAG_COLORS"
					:key="color"
					role="option"
					tabindex="0"
					class="cursor-pointer outline-none"
					:aria-selected="false"
					:data-color="color"
					:active="activeColor === color"
					@focus="activeColor = color"
					@click="finishCreate(color)"
					@keydown.enter.prevent="finishCreate(color)"
					@keydown.down.prevent="moveColorFocus($event, 1)"
					@keydown.up.prevent="moveColorFocus($event, -1)"
					@mouseenter="($event.currentTarget as HTMLElement).focus({ preventScroll: true })"
				>
					<TagBadge :color="color" :label="pendingLabel" />
					<template #suffix>
						<span class="text-sm capitalize text-ink-gray-5">{{ color }}</span>
					</template>
				</ItemListRow>
			</div>
		</div>
	</div>
</template>
