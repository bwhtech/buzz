<script setup lang="ts">
import { Button } from "frappe-ui"
import { ref, watch } from "vue"

// A logo centred on a quiet grey ground. Without an image it says so, or shows the
// placeholder prompt when the panel is an upload target. `editable` adds a Replace button.
const props = withDefaults(
	defineProps<{
		src?: string | null
		name?: string
		size?: "sm" | "lg"
		placeholder?: string
		editable?: boolean
		replacing?: boolean
	}>(),
	{ src: null, name: "", size: "sm", placeholder: "", editable: false, replacing: false },
)
defineEmits<{ replace: [] }>()

// A logo that fails to load reads as missing.
const failed = ref(false)
watch(
	() => props.src,
	() => (failed.value = false),
)
</script>

<template>
	<span
		class="relative flex w-full items-center justify-center rounded-4 bg-surface-gray-2"
		:class="size === 'lg' ? 'h-40 p-6' : 'h-24 p-4'"
	>
		<img
			v-if="src && !failed"
			:src="src"
			:alt="`${name} logo`"
			loading="lazy"
			class="max-h-full max-w-full object-contain"
			@error="failed = true"
		/>
		<span v-else class="flex flex-col items-center gap-2 text-ink-gray-5">
			<span
				class="size-6"
				:class="placeholder ? 'lucide-image-up' : 'lucide-image-off'"
				aria-hidden="true"
			/>
			<span :class="size === 'lg' ? 'text-base' : 'text-sm'">
				{{ placeholder || "Logo not provided" }}
			</span>
		</span>
		<Button
			v-if="editable"
			class="absolute bottom-2 right-2"
			size="sm"
			variant="outline"
			label="Replace"
			icon-left="lucide-images"
			:loading="replacing"
			@click="$emit('replace')"
		/>
	</span>
</template>
