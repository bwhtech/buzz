<script setup lang="ts">
import { FormControl } from "frappe-ui"
import { computed } from "vue"

import type { ThemeToken } from "@/types"

const props = defineProps<{ token: ThemeToken; fonts: string[]; disabled: boolean }>()
const value = defineModel<string>({ required: true })
const darkValue = defineModel<string | null>("darkValue", { default: null })

const label = computed(() => {
	const words = props.token.token.replaceAll("-", " ")
	return words.charAt(0).toUpperCase() + words.slice(1)
})

// The native picker only speaks #rrggbb; anything else is edited as text alone.
const isPickable = (colour: string | null) => /^#[0-9a-f]{6}$/i.test(colour ?? "")

const darkModel = computed({
	get: () => darkValue.value ?? "",
	set: (colour: string) => (darkValue.value = colour),
})

const colourModes = computed(() => [
	{ key: "light", label: __("Light"), model: value },
	{ key: "dark", label: __("Dark"), model: darkModel },
])
</script>

<template>
	<div v-if="token.type === 'Color'" class="space-y-1.5">
		<span class="text-p-sm text-ink-gray-7">{{ label }}</span>
		<div class="grid grid-cols-2 gap-2">
			<div v-for="mode in colourModes" :key="mode.key" class="flex items-center gap-1.5">
				<input
					v-if="isPickable(mode.model.value)"
					v-model="mode.model.value"
					type="color"
					:disabled="disabled"
					:aria-label="`${label} (${mode.label})`"
					class="size-7 shrink-0 cursor-pointer rounded-4 border border-outline-gray-2 bg-transparent disabled:cursor-not-allowed"
				/>
				<FormControl
					v-model="mode.model.value"
					class="min-w-0"
					:disabled="disabled"
					:aria-label="`${label} (${mode.label})`"
				/>
			</div>
		</div>
	</div>

	<div v-else class="flex items-center justify-between gap-3">
		<span class="text-p-sm text-ink-gray-7">{{ label }}</span>
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
</template>
