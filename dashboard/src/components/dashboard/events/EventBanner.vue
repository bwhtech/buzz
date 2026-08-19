<script setup lang="ts">
import { bannerPattern } from "@/utils/eventBanner";
import { refDebounced } from "@vueuse/core";
import { Button, ErrorMessage, FileUploader } from "frappe-ui";
import { computed, ref, watch } from "vue";

// The picker is filtered to these, and the file that comes back is checked against the
// same list: `accept` is a hint the OS may ignore, and a drag-drop never consults it.
// Raster only — an SVG banner would be same-origin markup, which a banner has no need
// to be. Neither check is enforcement; the upload endpoint takes what it is given.
const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp", "image/gif"];

function validateImage(file: File): string | void {
	if (!IMAGE_TYPES.includes(file.type)) {
		return "Choose a PNG, JPEG, WebP or GIF image";
	}
}

// The event title. The generated pattern is seeded by it, so a draft banner settles into
// the one the event keeps.
const props = defineProps<{ seed: string }>();

const image = defineModel<string>({ default: "" });

// Seeded off a debounced copy: a gradient cannot be transitioned, so re-seeding per
// keystroke would redraw the banner once per character while the organiser types. An
// untitled draft seeds on "Untitled" rather than the empty string, which would draw
// every new event the same.
const settledSeed = refDebounced(
	computed(() => props.seed.trim()),
	250
);

const pattern = computed(() => ({
	backgroundImage: bannerPattern(settledSeed.value || "Untitled"),
}));

// True from the first keystroke until the debounce fires — and the pattern swaps on the
// same tick it turns false. So the blur is already up when the swap lands, and only
// falls away afterwards, which is what hides the change.
const isSettling = computed(() => props.seed.trim() !== settledSeed.value);

// Reset per image, so a second upload fades in rather than snapping.
const loaded = ref(false);
watch(image, () => {
	loaded.value = false;
});
</script>

<template>
	<FileUploader
		:file-types="IMAGE_TYPES"
		:validate-file="validateImage"
		@success="(file: { file_url: string }) => (image = file.file_url)"
	>
		<template #default="{ openFileSelector, error: uploadError }">
			<!-- The whole banner is the hit area; the button inside stays the -->
			<!-- keyboard-reachable control, so its press must not fire twice. -->
			<div
				class="relative aspect-[3/1] cursor-pointer overflow-hidden rounded-xl border border-outline-gray-2"
				@click="openFileSelector"
			>
				<!-- The pattern gets a layer of its own so the blur below never
					 reaches the image or the button. Overscaled because blur samples
					 past the edges, which would otherwise go milky against the border.
					 A gradient cannot be interpolated, so blurring over the swap is
					 what hides it. -->
				<div
					class="absolute inset-0 scale-105 transition-[filter] duration-200 ease-out"
					:class="
						isSettling && !image ? 'blur-[10px] motion-reduce:blur-none' : 'blur-0'
					"
					:style="pattern"
					aria-hidden="true"
				/>

				<!-- Fades onto the pattern rather than replacing it outright. -->
				<!-- Absolute, like the pattern behind it: a static sibling would paint
					 under the positioned layer instead of over it. -->
				<img
					v-if="image"
					class="absolute inset-0 h-full w-full object-cover object-center transition-opacity duration-200 ease-out"
					:class="loaded ? 'opacity-100' : 'opacity-0'"
					:src="image"
					alt=""
					@load="loaded = true"
				/>

				<div class="absolute inset-0 grid place-items-center">
					<Button
						variant="subtle"
						icon-left="lucide-image-up"
						:label="image ? 'Change banner' : 'Add a banner'"
						@click.stop="openFileSelector"
					/>
				</div>
			</div>

			<!-- The slot types its error as {}, so the message needs narrowing. -->
			<ErrorMessage v-if="uploadError" class="mt-2" :message="String(uploadError)" />
		</template>
	</FileUploader>
</template>
