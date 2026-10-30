<template>
	<div class="space-y-1.5">
		<TextInput
			class="[&_input]:ps-[calc(var(--dial-code-width)+0.75rem)]"
			:style="{ '--dial-code-width': `${dialCodeWidth}px` }"
			type="tel"
			:label="__(label)"
			:required="required"
			:size="size"
			:variant="variant"
			:model-value="localNumber"
			@update:model-value="onNumberInput"
			:placeholder="placeholder || __('Phone number')"
		>
			<template #prefix>
				<span ref="dialCodePicker" class="-ms-1.5 inline-flex">
					<Combobox
						class="!gap-0.5 !px-1.5"
						trigger="button"
						variant="ghost"
						:size="size"
						:model-value="dialCode"
						@update:model-value="onDialCodeChange"
						:options="dialCodeOptions"
						:placeholder="__('Search')"
					/>
				</span>
			</template>
		</TextInput>
		<ErrorMessage v-if="error" :message="error" />
	</div>
</template>

<script setup lang="ts">
import { useElementSize } from "@vueuse/core"
import { Combobox, ErrorMessage, TextInput, useCall } from "frappe-ui"
import type { PropType } from "vue"
import { computed, ref, useTemplateRef, watch } from "vue"

import { DEFAULT_DIAL_CODE, formatPhone, parsePhone } from "@/utils/phone"

interface DialCode {
	code: string
	dial_code: string
}

const props = defineProps({
	modelValue: { type: String, default: "" },
	label: { type: String, default: "Phone" },
	placeholder: { type: String, default: "" },
	required: { type: Boolean, default: false },
	error: { type: String, default: "" },
	variant: { type: String as PropType<"subtle" | "outline" | "ghost">, default: "subtle" },
	size: { type: String as PropType<"sm" | "md" | "lg">, default: "sm" },
})

const emit = defineEmits(["update:modelValue"])

const dialCode = ref(DEFAULT_DIAL_CODE)
const localNumber = ref("")
const dialCodesData = ref<DialCode[]>([])
// The number is padded past the dial code picker, whose width follows the code.
const { width: dialCodeWidth } = useElementSize(useTemplateRef("dialCodePicker"))

function getFlagEmoji(countryCode: string) {
	if (!countryCode) return ""
	const codePoints = countryCode
		.toUpperCase()
		.split("")
		.map((char) => 127397 + char.charCodeAt(0))
	return String.fromCodePoint(...codePoints)
}

const dialCodeOptions = computed(() =>
	dialCodesData.value.map((d) => ({
		label: `${getFlagEmoji(d.code)} ${d.dial_code}`,
		value: d.dial_code,
	})),
)

const knownDialCodes = computed(() => dialCodesData.value.map((entry) => entry.dial_code))

function syncFromModel(value: string) {
	const { dialCode: parsedCode, localNumber: parsedNumber } = parsePhone(
		value,
		knownDialCodes.value,
	)
	if (parsedCode) dialCode.value = parsedCode
	localNumber.value = parsedNumber
}

syncFromModel(props.modelValue)

watch(
	() => props.modelValue,
	(val) => syncFromModel(val),
)

function emitValue() {
	emit("update:modelValue", formatPhone(dialCode.value, localNumber.value))
}

function onDialCodeChange(code: unknown) {
	if (code) {
		dialCode.value = String(code)
		emitValue()
	}
}

function onNumberInput(num: string) {
	const digitsOnly = String(num).replace(/\D/g, "")
	localNumber.value = digitsOnly
	emitValue()
}

useCall<DialCode[]>({
	url: "/api/v2/method/buzz.api.forms.get_dial_codes",
	onSuccess: (data) => {
		dialCodesData.value = data
		syncFromModel(props.modelValue)
	},
})
</script>
