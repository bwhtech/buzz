<script setup lang="ts">
import { TextInput } from "frappe-ui"

// A text field led by the fixed part of the value, such as a host or a profile URL.
defineProps<{ prefix: string; placeholder?: string; label: string; disabled?: boolean }>()
const value = defineModel<string>({ required: true })
</script>

<template>
	<!-- On a phone the prefix moves above the input in small type, as the event route field
	     does, so a long host leaves the slug the full width. -->
	<div
		class="flex min-w-0 items-stretch overflow-hidden rounded-4 border border-outline-gray-2 transition-colors duration-150 ease-[ease] hover:border-outline-gray-3 focus-within:border-outline-gray-4 motion-reduce:transition-none max-md:flex-col max-md:px-2.5 max-md:py-1.5"
	>
		<span
			class="flex shrink-0 items-center border-e border-outline-gray-2 bg-surface-gray-2 px-2 text-base text-ink-gray-6 max-md:border-0 max-md:bg-transparent max-md:px-0 max-md:text-xs max-md:leading-4 max-md:text-ink-gray-5"
		>
			{{ prefix }}
		</span>
		<TextInput
			v-model="value"
			variant="ghost"
			class="min-w-0 flex-1 max-md:[&_input]:!h-auto max-md:[&_input]:!px-0"
			:placeholder="placeholder"
			:aria-label="label"
			:disabled="disabled"
		/>
	</div>
</template>
