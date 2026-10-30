<script setup lang="ts">
import { Button, ErrorMessage } from "frappe-ui"
import { computed } from "vue"

import ImageCropUploader from "@/components/common/ImageCropUploader.vue"
import { validateIsImageFile } from "@/utils"

/**
 * The card a shared link shows, with the uploader that sets the image on it.
 * The image is `metaImage`; `image` is what to show while that is empty.
 */
const metaImage = defineModel<string | null | undefined>("metaImage", { required: true })
const props = defineProps<{
	image?: string | null
	title: string
	description: string
	// The address line on the card, such as "example.com/community/builders".
	site?: string
}>()

// Share images are 1200 × 630.
const ASPECT_RATIO = 1200 / 630
const site = computed(() => props.site || window.location.hostname)
</script>

<template>
	<ImageCropUploader
		:aspect-ratio="ASPECT_RATIO"
		:output-width="1200"
		output-type="image/jpeg"
		:validate-file="validateIsImageFile"
		@success="(file: { file_url: string }) => (metaImage = file.file_url)"
	>
		<template #default="{ openFileSelector, uploading, error }">
			<div class="overflow-hidden rounded-5 border border-outline-gray-2">
				<div class="relative aspect-[1200/630] border-b border-outline-gray-2 bg-surface-gray-2">
					<img v-if="props.image" :src="props.image" alt="" class="size-full object-cover" />
					<div class="absolute bottom-3 right-3 flex gap-1.5">
						<Button v-if="metaImage" label="Remove" class="shadow-sm" @click="metaImage = null" />
						<Button
							class="shadow-sm"
							icon-left="lucide-image-up"
							:label="metaImage ? 'Change image' : 'Upload image'"
							:loading="uploading"
							@click="openFileSelector"
						/>
					</div>
				</div>
				<div class="flex flex-col gap-1 bg-surface-base px-4 py-3">
					<span class="truncate text-p-sm text-ink-gray-5">{{ site }}</span>
					<span class="text-p-base font-semibold text-ink-gray-9">{{ props.title }}</span>
					<span class="line-clamp-2 text-p-sm text-ink-gray-6">{{ props.description }}</span>
				</div>
			</div>
			<ErrorMessage v-if="error" class="mt-2" :message="error" />
		</template>
	</ImageCropUploader>
</template>
