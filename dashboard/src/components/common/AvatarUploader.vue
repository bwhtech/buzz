<script setup lang="ts">
import { ErrorMessage, FileUploader, Spinner } from "frappe-ui"

import { validateIsImageFile } from "@/utils"

withDefaults(
	defineProps<{
		label: string
		title: string
		description?: string
		shape?: "circle" | "square"
	}>(),
	{ description: "", shape: "circle" },
)

const image = defineModel<string | null>({ required: true })
</script>

<template>
	<FileUploader
		:validate-file="validateIsImageFile"
		file-types="image/*"
		@success="(file: { file_url: string }) => (image = file.file_url)"
	>
		<template #default="{ openFileSelector, error: uploadError, uploading }">
			<div class="flex items-center gap-4">
				<button
					type="button"
					class="group relative size-16 shrink-0 overflow-hidden bg-surface-gray-3 transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] focus-visible:outline-none focus-visible:focus-ring active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100"
					:class="shape === 'circle' ? 'rounded-full' : 'rounded-6'"
					:aria-label="image ? __('Change photo') : __('Upload photo')"
					@click="openFileSelector"
				>
					<img v-if="image" :src="image" :alt="label" class="size-full object-cover" />
					<!-- Over an image the scrim is a hover affordance; over the empty
					     shape the camera is the only click cue. -->
					<span
						class="absolute inset-0 flex items-center justify-center transition-opacity duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
						:class="
							image
								? 'bg-black/40 opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100'
								: ''
						"
					>
						<Spinner
							v-if="uploading"
							class="size-5"
							:class="image ? 'text-white' : 'text-ink-gray-5'"
						/>
						<span
							v-else
							class="lucide-camera size-5"
							:class="image ? 'text-white' : 'text-ink-gray-5'"
						/>
					</span>
				</button>

				<div class="flex flex-col gap-1">
					<span class="text-base-medium text-ink-gray-8">{{ title }}</span>
					<p v-if="description" class="text-p-sm text-ink-gray-5">{{ description }}</p>
					<button
						v-if="image"
						type="button"
						class="self-start text-p-sm text-ink-gray-6 underline underline-offset-2 transition-colors duration-150 hover:text-ink-gray-8"
						@click="image = null"
					>
						{{ __("Remove") }}
					</button>
					<ErrorMessage :message="(uploadError as string) ?? ''" />
				</div>
			</div>
		</template>
	</FileUploader>
</template>
