<script setup lang="ts">
import { Button, Dialog, FormControl, MultiSelect, toast, useCall } from "frappe-ui"
import { computed, ref, watch } from "vue"

import type { FrappeError, TagItem } from "@/types"

// A team's tags for one kind of record; each change applies at once, outside any save bar.
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

const knownTags = computed(
	() => new Map([...props.options, ...applied.value].map((tag) => [tag.name, tag])),
)
const tagOptions = computed(() =>
	[...knownTags.value.values()].map((tag) => ({ label: tag.label, value: tag.name })),
)

const saveTags = useCall<
	TagItem[],
	{ document_type: string; document_name: string; tags: string[] }
>({ url: "/api/v2/method/buzz.api.tags.set_tags", method: "POST", immediate: false })
const newTagCall = useCall<TagItem, { team: string; document_type: string; label: string }>({
	url: "/api/v2/method/buzz.api.tags.create_tag",
	method: "POST",
	immediate: false,
})

const errorText = (error: unknown) =>
	(error as FrappeError).messages?.[0] ?? "Could not update tags"

async function setTags(names: string[], created: TagItem[] = []) {
	const previous = applied.value
	const known = new Map([...knownTags.value, ...created.map((tag) => [tag.name, tag] as const)])
	applied.value = names.flatMap((name) => known.get(name) ?? [])
	await saveTags.submit({
		document_type: props.documentType,
		document_name: props.documentName,
		tags: names,
	})
	if (saveTags.error) {
		applied.value = previous
		toast.error(errorText(saveTags.error))
		return
	}
	emit("changed")
}

const createDialogOpen = ref(false)
const newLabel = ref("")

function openCreateDialog(query: string, setOpen: (open: boolean) => void) {
	newLabel.value = query.trim()
	setOpen(false)
	createDialogOpen.value = true
}

// Naming a tag the team already has picks that tag rather than making a second one.
async function createTag() {
	await newTagCall.submit({
		team: props.team,
		document_type: props.documentType,
		label: newLabel.value,
	})
	if (newTagCall.error) return toast.error(errorText(newTagCall.error))
	createDialogOpen.value = false
	const tag = newTagCall.data!
	const names = applied.value.map((appliedTag) => appliedTag.name)
	if (!names.includes(tag.name)) await setTags([...names, tag.name], [tag])
}
</script>

<template>
	<MultiSelect
		label="Tags"
		placeholder="Add tags"
		:options="tagOptions"
		:model-value="applied.map((tag) => tag.name)"
		:disabled="disabled"
		empty-text="No tags yet"
		@update:model-value="setTags(($event as unknown[]).map(String))"
	>
		<template #summary="{ selectedOptions, summary }">
			{{ selectedOptions.map((option) => option.label).join(", ") || summary }}
		</template>
		<template #footer="{ query, setOpen }">
			<Button
				class="w-full !justify-start"
				variant="ghost"
				icon-left="lucide-plus"
				label="Create Tag"
				@click="openCreateDialog(query, setOpen)"
			/>
		</template>
	</MultiSelect>

	<Dialog v-model="createDialogOpen" size="sm" title="Create tag">
		<form class="space-y-4" @submit.prevent="createTag">
			<FormControl v-model="newLabel" label="Tag name" placeholder="Follow up" autocomplete="off" />
			<Button
				type="submit"
				variant="solid"
				class="w-full"
				label="Create Tag"
				:disabled="!newLabel.trim()"
				:loading="newTagCall.loading"
			/>
		</form>
	</Dialog>
</template>
