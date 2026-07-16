<template>
	<div class="space-y-1.5">
		<label class="text-xs text-ink-gray-5 block">
			{{ __(label) }}
			<span v-if="required" class="text-ink-red-4">*</span>
		</label>
		<div class="flex gap-1.5">
			<div class="w-24 shrink-0">
				<Combobox
					:model-value="null"
					@update:model-value="onDialCodeChange"
					:options="dialCodeOptions"
					variant="outline"
					:placeholder="shortDisplay"
				/>
			</div>
			<TextInput
				type="tel"
				:model-value="localNumber"
				@update:model-value="onNumberInput"
				:placeholder="placeholder || __('Phone number')"
			/>
		</div>
	</div>
</template>

<script setup>
import { DEFAULT_DIAL_CODE, formatPhone, parsePhone } from "@/utils/phone";
import { Combobox, TextInput, createResource } from "frappe-ui";
import { computed, ref, watch } from "vue";

const props = defineProps({
	modelValue: { type: String, default: "" },
	label: { type: String, default: "Phone" },
	placeholder: { type: String, default: "" },
	required: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const dialCode = ref(DEFAULT_DIAL_CODE);
const localNumber = ref("");
const dialCodesData = ref([]);

function getFlagEmoji(countryCode) {
	if (!countryCode) return "";
	const codePoints = countryCode
		.toUpperCase()
		.split("")
		.map((char) => 127397 + char.charCodeAt());
	return String.fromCodePoint(...codePoints);
}

const shortDisplay = computed(() => {
	const entry = dialCodesData.value.find((d) => d.dial_code === dialCode.value);
	if (entry) return `${getFlagEmoji(entry.code)} ${entry.dial_code}`;
	return dialCode.value;
});

const dialCodeOptions = computed(() =>
	dialCodesData.value.map((d) => ({
		label: `${getFlagEmoji(d.code)} ${d.dial_code}`,
		value: d.dial_code,
	}))
);

const knownDialCodes = computed(() => dialCodesData.value.map((entry) => entry.dial_code));

function syncFromModel(value) {
	const { dialCode: parsedCode, localNumber: parsedNumber } = parsePhone(
		value,
		knownDialCodes.value
	);
	if (parsedCode) dialCode.value = parsedCode;
	localNumber.value = parsedNumber;
}

syncFromModel(props.modelValue);

watch(
	() => props.modelValue,
	(val) => syncFromModel(val)
);

function emitValue() {
	emit("update:modelValue", formatPhone(dialCode.value, localNumber.value));
}

function onDialCodeChange(code) {
	if (code) {
		dialCode.value = code;
		emitValue();
	}
}

function onNumberInput(num) {
	const digitsOnly = String(num).replace(/\D/g, "");
	localNumber.value = digitsOnly;
	emitValue();
}

createResource({
	url: "buzz.api.forms.get_dial_codes",
	auto: true,
	onSuccess: (data) => {
		dialCodesData.value = data;
		syncFromModel(props.modelValue);
	},
});
</script>
