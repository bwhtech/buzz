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
	const applied = ref<TagItem[]>([])
	watch(
		() => source.tags,
		(tags) => (applied.value = [...tags]),
		{ immediate: true },
	)
	const appliedNames = computed(() => applied.value.map((tag) => tag.name))

	// Tags made here show in the menu before the parent reloads its options.
	const created = ref<TagItem[]>([])
	const options = computed(() => {
		const known = new Map([...source.options, ...created.value].map((tag) => [tag.name, tag]))
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

	async function setTags(tags: TagItem[]) {
		const previous = applied.value
		applied.value = tags
		await saveTags.submit({
			document_type: source.documentType,
			document_name: source.documentName,
			tags: tags.map((tag) => tag.name),
		})
		if (saveTags.error) {
			applied.value = previous
			toast.error(errorText(saveTags.error))
			return
		}
		onChanged()
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
			team: source.team,
			document_type: source.documentType,
			label,
			color,
		})
		if (newTagCall.error) return toast.error(errorText(newTagCall.error))
		const tag = newTagCall.data!
		created.value = [...created.value, tag]
		if (!appliedNames.value.includes(tag.name)) await setTags([...applied.value, tag])
	}

	return { applied, appliedNames, options, setTags, toggle, createTag }
}
