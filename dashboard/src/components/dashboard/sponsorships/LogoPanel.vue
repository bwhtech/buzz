<script setup lang="ts">
import { Avatar } from "frappe-ui"

// A logo centred on a quiet grey ground. Without an image it shows initials, or the
// placeholder prompt when the panel is an upload target.
withDefaults(
	defineProps<{ src?: string | null; name?: string; size?: "sm" | "lg"; placeholder?: string }>(),
	{ src: null, name: "", size: "sm", placeholder: "" },
)
</script>

<template>
	<span
		class="flex w-full items-center justify-center rounded-4 bg-surface-gray-2"
		:class="size === 'lg' ? 'h-40 p-6' : 'h-24 p-4'"
	>
		<img v-if="src" :src="src" :alt="`${name} logo`" class="max-h-full max-w-full object-contain" />
		<span v-else-if="placeholder" class="flex flex-col items-center gap-2 text-ink-gray-5">
			<span class="lucide-image-up size-6" aria-hidden="true" />
			<span class="text-base">{{ placeholder }}</span>
		</span>
		<Avatar v-else shape="square" :size="size === 'lg' ? '3xl' : 'xl'" :label="name" />
	</span>
</template>
