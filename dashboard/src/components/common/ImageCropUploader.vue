<script setup lang="ts">
import { Button, Dialog, ErrorMessage, useFileUpload } from "frappe-ui"
import { computed, ref, useTemplateRef } from "vue"

import ImageCropper from "@/components/common/ImageCropper.vue"

/**
 * Pick an image, crop it, then upload what was cropped.
 *
 * Shaped like frappe-ui's `FileUploader` on purpose — same `fileTypes` and
 * `validateFile` props, same `success`/`failure` emits, same slot props — so a host that
 * wants a crop swaps the tag and keeps everything else. The difference is that nothing
 * is sent until the organiser presses Save: the file picker hands over a `File`, the
 * dialog hands back a re-encoded blob, and only that blob is uploaded. Cancel aborts a
 * crop that is already uploading, so a slow request cannot land after it was dismissed.
 *
 * Public by default, unlike `FileUploader`. Every image this component uploads is read
 * without a session — a banner in a ticket email, an avatar on a public event page — and
 * a private file there is a broken image, not a locked one.
 */
const props = withDefaults(
	defineProps<{
		aspectRatio: number
		shape?: "circle" | "rect"
		outputWidth?: number
		fileTypes?: string | string[]
		validateFile?: (file: File) => string | void
		private?: boolean
		optimize?: boolean
	}>(),
	{
		shape: "rect",
		outputWidth: 1024,
		fileTypes: "image/*",
		validateFile: undefined,
		private: false,
		optimize: true,
	},
)

const emit = defineEmits<{
	success: [file: { file_url: string }]
	failure: [error: unknown]
}>()

const upload = useFileUpload()
const input = useTemplateRef<HTMLInputElement>("input")
const cropper = useTemplateRef<InstanceType<typeof ImageCropper>>("cropper")
const selected = ref<File | null>(null)
const isOpen = ref(false)
const pickError = ref("")
const pending = ref<AbortController | null>(null)

const accept = computed(() =>
	Array.isArray(props.fileTypes) ? props.fileTypes.join(",") : props.fileTypes || "image/*",
)
const uploading = computed(() => upload.isUploading.value)
const error = computed(() => pickError.value || errorText(upload.error.value))

function errorText(reason: unknown): string {
	if (!reason) return ""
	if (reason instanceof Error) return reason.message
	return String(reason)
}

function openFileSelector() {
	pickError.value = ""
	input.value?.click()
}

function selectFile(event: Event) {
	const target = event.target as HTMLInputElement
	const file = target.files?.[0]
	// Cleared straight away, so choosing the same file twice in a row still fires.
	target.value = ""
	if (!file) return

	const message = props.validateFile?.(file)
	if (message) {
		pickError.value = message
		return
	}

	upload.reset()
	selected.value = file
	isOpen.value = true
}

async function save() {
	pickError.value = ""
	const controller = new AbortController()
	pending.value = controller

	try {
		// Cropping is inside the try because a canvas export can throw on an image the
		// browser has not finished decoding, and that belongs in the dialog, not in an
		// unhandled rejection.
		const blob = await cropper.value?.getCroppedBlob()
		if (!blob) {
			pickError.value = __("Could not crop the image")
			return
		}

		const cropped = new File([blob], croppedName(selected.value, blob.type), { type: blob.type })
		const file = await upload.upload(cropped, {
			private: props.private,
			optimize: props.optimize,
			signal: controller.signal,
		})
		isOpen.value = false
		emit("success", file)
	} catch (uploadError) {
		// Cancel aborts the request rather than letting it land, so its rejection is the
		// outcome the organiser asked for, not a failure to report.
		if (controller.signal.aborted) return
		emit("failure", uploadError)
	} finally {
		if (pending.value === controller) pending.value = null
	}
}

/** Keeps the original name recognisable in the file list, with the new extension. */
function croppedName(file: File | null, type: string) {
	const stem = file?.name.replace(/\.[^.]+$/, "")
	return `${stem || "image"}-cropped.${type === "image/png" ? "png" : "jpg"}`
}

// Every way out of the dialog lands here — Cancel, Escape, the overlay — so this is the
// one place an upload still in flight gets abandoned rather than left to land later. The
// reset clears the "Upload cancelled" the abort leaves behind: the organiser asked for
// that, and reporting it back to them as an error is just noise.
function clearFile() {
	pending.value?.abort()
	upload.reset()
	selected.value = null
}
</script>

<template>
	<input
		ref="input"
		type="file"
		class="hidden"
		:accept="accept"
		aria-hidden="true"
		tabindex="-1"
		@change="selectFile"
	/>

	<slot v-bind="{ openFileSelector, uploading, progress: upload.progress.value, error }" />

	<Dialog v-model="isOpen" :title="__('Crop image')" size="xl" @after-leave="clearFile">
		<div v-if="selected" class="space-y-5">
			<ImageCropper
				ref="cropper"
				:file="selected"
				:aspect-ratio="aspectRatio"
				:shape="shape"
				:output-width="outputWidth"
			/>

			<ErrorMessage :message="error" />

			<div class="flex items-center justify-between gap-3">
				<Button variant="ghost" :label="__('Reset')" @click="cropper?.resetCrop()" />
				<div class="flex items-center gap-2">
					<Button :label="__('Cancel')" @click="isOpen = false" />
					<Button variant="solid" :loading="uploading" :label="__('Save')" @click="save" />
				</div>
			</div>
		</div>
	</Dialog>
</template>
