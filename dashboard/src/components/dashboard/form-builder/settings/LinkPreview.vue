<script setup lang="ts">
import { ErrorMessage, Textarea, TextInput } from "frappe-ui"
import { computed } from "vue"

import SharePreviewCard from "@/components/common/SharePreviewCard.vue"
import { wallClockDate, wallClockIn } from "@/utils/timeZones"

import type { BuzzFormDoc } from "../useFormBuilder"

const form = defineModel<BuzzFormDoc>({ required: true })
// The server picks the same fallbacks for the shared link: the form's image, then the event's.
const props = defineProps<{
	eventTitle: string
	eventDescription?: string | null
	eventImage?: string | null
	eventTimeZone?: string | null
	// What the form collects, such as "proposals".
	noun: string
	// The booking page names itself; other forms pair their title with the event's.
	defaultTitle?: string
}>()

const image = computed(() => form.value.meta_image || form.value.og_image || props.eventImage)
const title = computed(() => props.defaultTitle || `${form.value.title} · ${props.eventTitle}`)

// The close date is on the event's clock, as the server compares it.
const closingNote = computed(() => {
	const closeAt = form.value.auto_close_at
	if (!closeAt || closeAt <= wallClockIn(props.eventTimeZone)) return ""
	const date = wallClockDate(closeAt).toLocaleDateString(undefined, {
		day: "numeric",
		month: "short",
		timeZone: "UTC",
	})
	const noun = props.noun.charAt(0).toUpperCase() + props.noun.slice(1)
	return `${noun} close on ${date}.`
})
const description = computed(() =>
	[form.value.description || props.eventDescription, closingNote.value].filter(Boolean).join(" "),
)
</script>

<template>
	<div class="flex flex-col gap-4 p-4">
		<SharePreviewCard
			v-model:meta-image="form.meta_image"
			:image="image"
			:title="form.meta_title || title"
			:description="form.meta_description || description"
		/>
		<p v-if="!form.meta_image && !defaultTitle" class="-mt-2 text-p-sm text-ink-gray-5">
			Without an upload, the link shows an image made from the form's title and the event's banner,
			drawn when you save.
		</p>
		<p v-else-if="!form.meta_image" class="-mt-2 text-p-sm text-ink-gray-5">
			Without an upload, the link shows the event's share image.
		</p>
		<TextInput
			:model-value="form.meta_title ?? ''"
			@update:model-value="form.meta_title = $event"
			label="Preview title"
			:placeholder="title"
		/>
		<Textarea
			v-model="form.meta_description"
			label="Preview description"
			:placeholder="description"
			:rows="2"
		/>
	</div>
</template>
