<script setup lang="ts">
import { Avatar, Button } from "frappe-ui"

// A logo centred on a quiet grey ground. Without an image it shows initials, or the
// placeholder prompt when the panel is an upload target. `editable` adds a Replace button.
withDefaults(
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
</script>

<template>
	<span
		class="relative flex w-full items-center justify-center rounded-4 bg-surface-gray-2"
		:class="size === 'lg' ? 'h-40 p-6' : 'h-24 p-4'"
	>
		<img v-if="src" :src="src" :alt="`${name} logo`" class="max-h-full max-w-full object-contain" />
		<span v-else-if="placeholder" class="flex flex-col items-center gap-2 text-ink-gray-5">
			<span class="lucide-image-up size-6" aria-hidden="true" />
			<span class="text-base">{{ placeholder }}</span>
		</span>
		<Avatar v-else shape="square" :size="size === 'lg' ? '3xl' : 'xl'" :label="name" />
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
