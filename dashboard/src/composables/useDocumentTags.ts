import { toast, useCall } from "frappe-ui"
import { computed, ref, watch } from "vue"

import type { FrappeError, TagColor, TagItem } from "@/types"

type DocumentTagsSource = {
	team: string
	documentType: string
	documentName: string
	tags: TagItem[]
	options: TagItem[]
}

const errorText = (error: unknown) =>
	(error as FrappeError).messages?.[0] ?? "Could not update tags"

// A record's tags, applied at once and shown before the server answers.
export function useDocumentTags(source: DocumentTagsSource, onChanged: () => void) {
	const appliedTags = ref<TagItem[]>([])
	watch(
		() => source.tags,
		(tags) => (appliedTags.value = [...tags]),
		{ immediate: true },
	)
	const appliedNames = computed(() => appliedTags.value.map((tag) => tag.name))

	// Tags made here show in the menu before the parent reloads its options.
	const createdTags = ref<TagItem[]>([])
	const options = computed(() => {
		const known = new Map([...source.options, ...createdTags.value].map((tag) => [tag.name, tag]))
		return [...known.values()]
	})

	const setTagsCall = useCall<
		TagItem[],
		{ document_type: string; document_name: string; tags: string[] }
	>({ url: "/api/v2/method/buzz.api.tags.set_tags", method: "POST", immediate: false })
	const createTagCall = useCall<
		TagItem,
		{ team: string; document_type: string; label: string; color: TagColor }
	>({ url: "/api/v2/method/buzz.api.tags.create_tag", method: "POST", immediate: false })

	async function setTags(tags: TagItem[]) {
		const previous = appliedTags.value
		appliedTags.value = tags
		await setTagsCall.submit({
			document_type: source.documentType,
			document_name: source.documentName,
			tags: tags.map((tag) => tag.name),
		})
		if (setTagsCall.error) {
			appliedTags.value = previous
			toast.error(errorText(setTagsCall.error))
			return
		}
		onChanged()
	}

	function removeTag(tag: TagItem) {
		setTags(appliedTags.value.filter((each) => each.name !== tag.name))
	}

	// Naming a tag the team already has picks that tag rather than making a second one.
	async function createTag(label: string, color: TagColor) {
		await createTagCall.submit({
			team: source.team,
			document_type: source.documentType,
			label,
			color,
		})
		if (createTagCall.error) return toast.error(errorText(createTagCall.error))
		const tag = createTagCall.data!
		createdTags.value = [...createdTags.value, tag]
		if (!appliedNames.value.includes(tag.name)) await setTags([...appliedTags.value, tag])
	}

	return { appliedTags, appliedNames, options, setTags, removeTag, createTag }
}
