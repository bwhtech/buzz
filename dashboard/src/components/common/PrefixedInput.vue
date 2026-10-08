<script setup lang="ts">
import { TextInput } from "frappe-ui"

// A text field led by the fixed part of the value, such as a host or a profile URL.
defineProps<{ prefix: string; placeholder?: string; label: string; disabled?: boolean }>()
const value = defineModel<string>({ required: true })
</script>

<template>
	<div
		class="flex min-w-0 items-stretch overflow-hidden rounded-4 border border-outline-gray-2 transition-colors duration-150 ease-out hover:border-outline-gray-3 focus-within:border-outline-gray-4 motion-reduce:transition-none"
	>
		<span
			class="flex shrink-0 items-center border-e border-outline-gray-2 bg-surface-gray-2 px-2 text-base text-ink-gray-6"
		>
			{{ prefix }}
		</span>
		<TextInput
			v-model="value"
			variant="ghost"
			class="min-w-0 flex-1"
			:placeholder="placeholder"
			:aria-label="label"
			:disabled="disabled"
		/>
	</div>
</template>
