<script setup lang="ts">
import { Button, ErrorMessage, Textarea, TextInput } from "frappe-ui"
import { computed } from "vue"

import ImageCropUploader from "@/components/common/ImageCropUploader.vue"
import { validateIsImageFile } from "@/utils"
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

const host = window.location.hostname
// Share images are 1200 × 630.
const ASPECT_RATIO = 1200 / 630

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
		<ImageCropUploader
			:aspect-ratio="ASPECT_RATIO"
			:output-width="1200"
			output-type="image/jpeg"
			:validate-file="validateIsImageFile"
			@success="(file: { file_url: string }) => (form.meta_image = file.file_url)"
		>
			<template #default="{ openFileSelector, uploading, error }">
				<div class="overflow-hidden rounded-5 border border-outline-gray-2">
					<div class="relative aspect-[1200/630] border-b border-outline-gray-2 bg-surface-gray-2">
						<img v-if="image" :src="image" alt="" class="size-full object-cover" />
						<div class="absolute bottom-3 right-3 flex gap-1.5">
							<Button
								v-if="form.meta_image"
								label="Remove"
								class="shadow-sm"
								@click="form.meta_image = null"
							/>
							<Button
								class="shadow-sm"
								icon-left="lucide-image-up"
								:label="form.meta_image ? 'Change image' : 'Upload image'"
								:loading="uploading"
								@click="openFileSelector"
							/>
						</div>
					</div>
					<div class="flex flex-col gap-1 bg-surface-base px-4 py-3">
						<span class="truncate text-p-sm text-ink-gray-5">{{ host }}</span>
						<span class="text-p-base font-semibold text-ink-gray-9">
							{{ form.meta_title || title }}
						</span>
						<span class="line-clamp-2 text-p-sm text-ink-gray-6">
							{{ form.meta_description || description }}
						</span>
					</div>
				</div>
				<ErrorMessage v-if="error" class="mt-2" :message="error" />
			</template>
		</ImageCropUploader>
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
