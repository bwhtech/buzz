<script setup lang="ts">
import { Popover, toast, useCall } from "frappe-ui"
import { computed, ref, watch } from "vue"

import TagBadge from "@/components/common/tags/TagBadge.vue"
import TagMenu from "@/components/common/tags/TagMenu.vue"
import type { FrappeError, TagColor, TagItem } from "@/types"

// A record's tags as a chip row; each change applies at once, outside any save bar.
const props = defineProps<{
	team: string
	documentType: string
	documentName: string
	tags: TagItem[]
	options: TagItem[]
	disabled?: boolean
}>()
const emit = defineEmits<{ changed: [] }>()

// Shown before the server answers; the parent's reload brings the saved tags back in.
const applied = ref<TagItem[]>([])
watch(
	() => props.tags,
	(tags) => (applied.value = [...tags]),
	{ immediate: true },
)
const appliedNames = computed(() => applied.value.map((tag) => tag.name))

// Tags made here show in the menu before the parent reloads its options.
const created = ref<TagItem[]>([])
const menuOptions = computed(() => {
	const known = new Map([...props.options, ...created.value].map((tag) => [tag.name, tag]))
	return [...known.values()]
})

const saveTags = useCall<
	TagItem[],
	{ document_type: string; document_name: string; tags: string[] }
>({ url: "/api/v2/method/buzz.api.tags.set_tags", method: "POST", immediate: false })
const newTagCall = useCall<
	TagItem,
	{ team: string; document_type: string; label: string; color: TagColor }
>({ url: "/api/v2/method/buzz.api.tags.create_tag", method: "POST", immediate: false })

const errorText = (error: unknown) =>
	(error as FrappeError).messages?.[0] ?? "Could not update tags"

async function setTags(tags: TagItem[]) {
	const previous = applied.value
	applied.value = tags
	await saveTags.submit({
		document_type: props.documentType,
		document_name: props.documentName,
		tags: tags.map((tag) => tag.name),
	})
	if (saveTags.error) {
		applied.value = previous
		toast.error(errorText(saveTags.error))
		return
	}
	emit("changed")
}

function toggle(tag: TagItem) {
	const isApplied = appliedNames.value.includes(tag.name)
	setTags(
		isApplied ? applied.value.filter((each) => each.name !== tag.name) : [...applied.value, tag],
	)
}

// Naming a tag the team already has picks that tag rather than making a second one.
async function createTag(label: string, color: TagColor) {
	await newTagCall.submit({
		team: props.team,
		document_type: props.documentType,
		label,
		color,
	})
	if (newTagCall.error) return toast.error(errorText(newTagCall.error))
	const tag = newTagCall.data!
	created.value = [...created.value, tag]
	if (!appliedNames.value.includes(tag.name)) await setTags([...applied.value, tag])
}
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
		<Popover v-if="!disabled">
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
			<TagMenu
				:options="menuOptions"
				:selected="appliedNames"
				@toggle="toggle"
				@create="createTag"
			/>
		</Popover>
	</div>
</template>
