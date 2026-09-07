<script setup lang="ts">
import { Button, Slider } from "frappe-ui"
import { computed, nextTick, onBeforeUnmount, ref, useTemplateRef, watch } from "vue"

import { clampOffset, coverScale, rotatedSize, type Point } from "@/utils/imageCrop"

const MIN_ZOOM = 100
const MAX_ZOOM = 300

const props = withDefaults(
	defineProps<{
		file: File
		/** Width over height of the crop, matching the frame the image will end up in. */
		aspectRatio: number
		shape?: "circle" | "rect"
		/** Long edge of the exported image; the short one follows from the ratio. */
		outputWidth?: number
	}>(),
	{ shape: "rect", outputWidth: 1024 },
)

const frame = useTemplateRef<HTMLElement>("frame")
const image = useTemplateRef<HTMLImageElement>("image")
const imageUrl = ref("")
const imageSize = ref<{ width: number; height: number } | null>(null)
const offset = ref<Point>({ x: 0, y: 0 })
const rotation = ref(0)
// Slider works in arrays, and in whole percent so its steps land somewhere predictable.
const zoomPercent = ref([MIN_ZOOM])
const dragPointer = ref<number | null>(null)
const dragStart = ref<Point>({ x: 0, y: 0 })
const dragOrigin = ref<Point>({ x: 0, y: 0 })

const zoom = computed(() => zoomPercent.value[0] / 100)
const frameSize = computed(() => {
	const width = frame.value?.getBoundingClientRect().width || 0
	return { width, height: width / props.aspectRatio }
})
const turnedSize = computed(() =>
	imageSize.value ? rotatedSize(imageSize.value, rotation.value) : null,
)
// The scale that covers the frame before the organiser zooms past it.
const baseScale = computed(() =>
	turnedSize.value ? coverScale(turnedSize.value, frameSize.value) : 1,
)
const renderedSize = computed(() => {
	if (!turnedSize.value) return null
	const scale = baseScale.value * zoom.value
	return { width: turnedSize.value.width * scale, height: turnedSize.value.height * scale }
})

const wrapStyle = computed(() => ({
	transform: `translate(-50%, -50%) translate(${offset.value.x}px, ${offset.value.y}px)`,
}))
// Rotation and zoom ride on the element's own transform, so the wrapper above is left
// holding nothing but the pan — which is the only thing a drag has to change.
const imageStyle = computed(() => {
	if (!imageSize.value) return {}
	return {
		width: `${imageSize.value.width * baseScale.value}px`,
		height: `${imageSize.value.height * baseScale.value}px`,
		transform: `rotate(${rotation.value}deg) scale(${zoom.value})`,
	}
})

watch(
	() => props.file,
	async (file) => {
		releaseImageUrl()
		imageUrl.value = URL.createObjectURL(file)
		imageSize.value = await readImageSize(imageUrl.value)
		resetCrop()
		// The frame has no width until it is laid out, and every bound is measured off it.
		await nextTick()
		constrain()
	},
	{ immediate: true },
)

watch([zoomPercent, rotation], constrain)

onBeforeUnmount(() => {
	releaseImageUrl()
	stopListening()
})

function resetCrop() {
	offset.value = { x: 0, y: 0 }
	rotation.value = 0
	zoomPercent.value = [MIN_ZOOM]
}

function rotate() {
	rotation.value = (rotation.value + 90) % 360
}

function nudgeZoom(delta: number) {
	zoomPercent.value = [Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoomPercent.value[0] + delta))]
}

function startDrag(event: PointerEvent) {
	if (!frame.value) return
	frame.value.setPointerCapture(event.pointerId)
	dragPointer.value = event.pointerId
	dragStart.value = { x: event.clientX, y: event.clientY }
	dragOrigin.value = { ...offset.value }
	window.addEventListener("pointermove", drag)
	window.addEventListener("pointerup", stopDrag)
	window.addEventListener("pointercancel", stopDrag)
}

function drag(event: PointerEvent) {
	if (dragPointer.value === null) return
	offset.value = bound({
		x: dragOrigin.value.x + event.clientX - dragStart.value.x,
		y: dragOrigin.value.y + event.clientY - dragStart.value.y,
	})
}

function stopDrag(event: PointerEvent) {
	if (dragPointer.value !== event.pointerId) return
	dragPointer.value = null
	stopListening()
}

function stopListening() {
	window.removeEventListener("pointermove", drag)
	window.removeEventListener("pointerup", stopDrag)
	window.removeEventListener("pointercancel", stopDrag)
}

function constrain() {
	offset.value = bound(offset.value)
}

function bound(point: Point) {
	if (!renderedSize.value || !frameSize.value.width) return point
	return clampOffset(point, renderedSize.value, frameSize.value)
}

/**
 * The crop, as a JPEG.
 *
 * The canvas replays exactly what is on screen, scaled up from the frame's rendered
 * width to the export width — so what the organiser lined up is what gets stored, and
 * nothing downstream has to know a crop happened.
 */
async function getCroppedBlob(): Promise<Blob | null> {
	const source = image.value
	const size = imageSize.value
	const width = frameSize.value.width
	if (!source || !size || !width) return null

	const canvas = document.createElement("canvas")
	canvas.width = props.outputWidth
	canvas.height = Math.round(props.outputWidth / props.aspectRatio)
	const context = canvas.getContext("2d")
	if (!context) return null

	const exportRatio = props.outputWidth / width
	const scale = baseScale.value * zoom.value * exportRatio
	context.translate(
		canvas.width / 2 + offset.value.x * exportRatio,
		canvas.height / 2 + offset.value.y * exportRatio,
	)
	context.rotate((rotation.value * Math.PI) / 180)
	context.scale(scale, scale)
	context.drawImage(source, -size.width / 2, -size.height / 2)

	return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92))
}

function releaseImageUrl() {
	if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
	imageUrl.value = ""
}

function readImageSize(url: string) {
	return new Promise<{ width: number; height: number } | null>((resolve) => {
		const probe = new Image()
		probe.addEventListener(
			"load",
			() => resolve({ width: probe.naturalWidth, height: probe.naturalHeight }),
			{ once: true },
		)
		probe.addEventListener("error", () => resolve(null), { once: true })
		probe.src = url
	})
}

defineExpose({ getCroppedBlob, resetCrop })
</script>

<template>
	<div class="space-y-4">
		<div
			ref="frame"
			class="relative w-full select-none overflow-hidden rounded-6 bg-surface-gray-3 touch-none"
			:class="dragPointer === null ? 'cursor-grab' : 'cursor-grabbing'"
			:style="{ aspectRatio: String(aspectRatio) }"
			@pointerdown="startDrag"
			@wheel.prevent="nudgeZoom($event.deltaY > 0 ? -8 : 8)"
		>
			<div
				v-if="imageUrl && imageSize"
				class="absolute left-1/2 top-1/2 will-change-transform"
				:style="wrapStyle"
			>
				<img
					ref="image"
					:src="imageUrl"
					alt=""
					draggable="false"
					class="max-w-none select-none"
					:style="imageStyle"
				/>
			</div>

			<!-- The mask is the crop's own outline: everything outside it is what the
				 frame will cut off. A ring rather than a fill, so the picture underneath
				 stays visible while it is being placed. -->
			<div
				v-if="shape === 'circle'"
				class="pointer-events-none absolute inset-[7%] rounded-full border-2 border-white shadow-[0_0_0_999px_rgba(0,0,0,0.28)]"
			/>

			<Button
				class="absolute right-3 top-3"
				icon="lucide-rotate-cw"
				:label="__('Rotate')"
				@pointerdown.stop
				@click.stop="rotate"
			/>
		</div>

		<div class="flex items-center gap-3">
			<Button variant="ghost" icon="lucide-minus" :label="__('Zoom out')" @click="nudgeZoom(-10)" />
			<Slider v-model="zoomPercent" class="min-w-0 flex-1" :min="MIN_ZOOM" :max="MAX_ZOOM" />
			<Button variant="ghost" icon="lucide-plus" :label="__('Zoom in')" @click="nudgeZoom(10)" />
		</div>
	</div>
</template>
