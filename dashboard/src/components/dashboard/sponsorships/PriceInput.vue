<script setup lang="ts">
import { TextInput } from "frappe-ui"
import { computed, ref } from "vue"

import { formatNumber, numberFormatSeparators, parseNumber } from "@/utils/currency"

const price = defineModel<number>({ required: true })
const props = defineProps<{
	currencySymbol: string
	numberFormat?: string | null
	label?: string
	disabled?: boolean
}>()

// Grouped while at rest, raw while typing so the caret never jumps over inserted separators.
const isFocused = ref(false)
const typedText = ref("")

const displayValue = computed(() =>
	isFocused.value ? typedText.value : formatNumber(price.value || 0, props.numberFormat),
)

function onFocus() {
	const { decimalSeparator } = numberFormatSeparators(props.numberFormat)
	typedText.value = price.value ? String(price.value).replace(".", decimalSeparator || ".") : ""
	isFocused.value = true
}

function onInput(value: string) {
	typedText.value = value
	price.value = parseNumber(value, props.numberFormat)
}
</script>

<template>
	<TextInput
		:model-value="displayValue"
		:label="label"
		inputmode="decimal"
		autocomplete="off"
		:disabled="disabled"
		@update:model-value="onInput"
		@focus="onFocus"
		@blur="isFocused = false"
	>
		<template #prefix>
			<span class="text-base text-ink-gray-5">{{ currencySymbol }}</span>
		</template>
	</TextInput>
</template>
