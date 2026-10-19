<script setup lang="ts">
import { Button } from "frappe-ui"

const props = defineProps<{
	question: string
	placeholder: string
	cta: string
	disabled?: boolean
	loading?: boolean
	// Rewrites each keystroke, so the field never shows what the value cannot hold.
	format?: (value: string) => string
}>()
const emit = defineEmits<{ submit: [] }>()
const value = defineModel<string>({ required: true })

function onInput(event: Event) {
	const input = event.target as HTMLInputElement
	const formatted = props.format ? props.format(input.value) : input.value
	input.value = formatted
	value.value = formatted
}

const submit = () => props.disabled || props.loading || emit("submit")
</script>

<template>
	<form class="flex flex-col gap-5" @submit.prevent="submit">
		<slot name="back" />
		<label class="flex flex-col gap-5">
			<span class="text-base text-ink-gray-5">{{ question }}</span>
			<input
				:value="value"
				:placeholder="placeholder"
				class="w-full border-0 border-b border-outline-gray-2 bg-transparent pb-3 text-[32px] font-semibold tracking-[-0.035em] text-ink-gray-9 outline-none transition-colors duration-150 placeholder:text-ink-gray-3 focus:border-outline-gray-5 sm:text-[44px] sm:leading-[1.1]"
				autocomplete="off"
				spellcheck="false"
				@input="onInput"
			/>
		</label>
		<div class="min-h-5 text-base text-ink-gray-5" aria-live="polite">
			<slot name="status" />
		</div>
		<div class="flex items-center gap-3 pt-2">
			<Button
				variant="solid"
				size="lg"
				type="submit"
				icon-right="lucide-arrow-right"
				:label="cta"
				:disabled="disabled"
				:loading="loading"
			/>
			<span class="flex items-center gap-1.5 text-sm text-ink-gray-5 max-sm:hidden">
				{{ __("or press") }}
				<kbd
					class="rounded-2 border border-outline-gray-2 px-1.5 font-sans text-xs text-ink-gray-6"
				>
					Enter
				</kbd>
			</span>
		</div>
	</form>
</template>
