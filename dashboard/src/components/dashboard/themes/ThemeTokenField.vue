<script setup lang="ts">
import { FormControl } from "frappe-ui"
import { computed } from "vue"

import type { ThemeToken } from "@/types"

const props = defineProps<{ token: ThemeToken; fonts: string[]; disabled: boolean }>()
const value = defineModel<string>({ required: true })

const label = computed(() => {
	const words = props.token.token.replaceAll("-", " ")
	return words.charAt(0).toUpperCase() + words.slice(1)
})

// The native picker only speaks #rrggbb; anything else is edited as text alone.
const isPickable = computed(() => /^#[0-9a-f]{6}$/i.test(value.value))
</script>

<template>
	<div class="flex items-center justify-between gap-3">
		<span class="text-p-sm text-ink-gray-7">{{ label }}</span>
		<div class="flex items-center gap-2">
			<input
				v-if="token.type === 'Color' && isPickable"
				v-model="value"
				type="color"
				:disabled="disabled"
				:aria-label="label"
				class="size-7 cursor-pointer rounded-4 border border-outline-gray-2 bg-transparent disabled:cursor-not-allowed"
			/>
			<FormControl
				v-if="token.type === 'Font'"
				v-model="value"
				type="select"
				class="w-36"
				:options="fonts"
				:disabled="disabled"
				:aria-label="label"
			/>
			<FormControl v-else v-model="value" class="w-28" :disabled="disabled" :aria-label="label" />
		</div>
	</div>
</template>
